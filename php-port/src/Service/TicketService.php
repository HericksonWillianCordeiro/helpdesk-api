<?php

declare(strict_types=1);

namespace App\Service;

use App\Entity\Ticket;
use App\Entity\TicketComment;
use App\Entity\User;
use App\Repository\CategoryRepository;
use App\Repository\TicketRepository;
use App\Repository\UserRepository;
use Doctrine\ORM\EntityManagerInterface;

/**
 * Serviço de tickets — equivalente às rotas /tickets do projeto Python.
 */
class TicketService
{
    public function __construct(
        private readonly TicketRepository   $ticketRepo,
        private readonly CategoryRepository $categoryRepo,
        private readonly UserRepository     $userRepo,
        private readonly EntityManagerInterface $em,
    ) {}

    // -------------------------------------------------------------------------
    // CRUD
    // -------------------------------------------------------------------------

    public function create(User $requester, array $data): Ticket
    {
        $category = $this->categoryRepo->find($data['category_id'] ?? 0);
        if ($category === null || !$category->isActive()) {
            throw new \RuntimeException('Categoria não encontrada.', 404);
        }

        $ticket = (new Ticket())
            ->setTitle(trim($data['title']))
            ->setDescription(trim($data['description']))
            ->setPriority($data['priority'] ?? Ticket::PRIORITY_MEDIUM)
            ->setRequester($requester)
            ->setCategory($category);

        $ticket->calculateSlaDeadline();

        $this->em->persist($ticket);
        $this->em->flush();

        return $ticket;
    }

    public function list(User $viewer, array $filters = [], int $page = 1, int $limit = 20): array
    {
        return $this->ticketRepo->findFiltered(
            viewer:     $viewer,
            status:     $filters['status']      ?? null,
            priority:   $filters['priority']    ?? null,
            categoryId: isset($filters['category']) ? (int) $filters['category'] : null,
            techId:     isset($filters['technician']) ? (int) $filters['technician'] : null,
            page:       $page,
            limit:      min($limit, 100),
        );
    }

    public function get(int $id, User $viewer): Ticket
    {
        $ticket = $this->ticketRepo->find($id);

        if ($ticket === null) {
            throw new \RuntimeException('Ticket não encontrado.', 404);
        }

        $this->assertCanView($ticket, $viewer);

        return $ticket;
    }

    public function updateStatus(int $id, User $viewer, string $newStatus, ?string $note = null): Ticket
    {
        $ticket = $this->get($id, $viewer);

        if ($ticket->getStatus() === Ticket::STATUS_CLOSED) {
            throw new \RuntimeException('Tickets fechados não podem ser alterados.', 422);
        }

        if (!$viewer->isAdmin() && !$viewer->isTechnician()) {
            throw new \RuntimeException('Apenas técnicos e administradores podem alterar o status.', 403);
        }

        $ticket->setStatus($newStatus);

        if ($newStatus === Ticket::STATUS_RESOLVED) {
            $ticket->setResolvedAt(new \DateTimeImmutable());

            // Nota de resolução obrigatória vira comentário — igual ao projeto Python
            if (!empty($note)) {
                $comment = (new TicketComment())
                    ->setTicket($ticket)
                    ->setAuthor($viewer)
                    ->setContent($note);
                $this->em->persist($comment);
            }
        } else {
            $ticket->setResolvedAt(null);
        }

        $this->em->flush();

        return $ticket;
    }

    public function assign(int $id, User $admin, int $technicianId): Ticket
    {
        if (!$admin->isAdmin()) {
            throw new \RuntimeException('Apenas administradores podem atribuir técnicos.', 403);
        }

        $ticket     = $this->get($id, $admin);
        $technician = $this->userRepo->find($technicianId);

        if ($technician === null || !$technician->isTechnician() || !$technician->isActive()) {
            throw new \RuntimeException('Técnico não encontrado ou inativo.', 404);
        }

        $ticket->setTechnician($technician);
        $this->em->flush();

        return $ticket;
    }

    public function delete(int $id, User $admin): void
    {
        if (!$admin->isAdmin()) {
            throw new \RuntimeException('Apenas administradores podem excluir tickets.', 403);
        }

        $ticket = $this->ticketRepo->find($id);
        if ($ticket === null) {
            throw new \RuntimeException('Ticket não encontrado.', 404);
        }

        $this->em->remove($ticket);
        $this->em->flush();
    }

    // -------------------------------------------------------------------------
    // Comentários
    // -------------------------------------------------------------------------

    public function addComment(int $ticketId, User $author, string $content): TicketComment
    {
        $ticket = $this->get($ticketId, $author);

        $comment = (new TicketComment())
            ->setTicket($ticket)
            ->setAuthor($author)
            ->setContent(trim($content));

        $this->em->persist($comment);
        $this->em->flush();

        return $comment;
    }

    // -------------------------------------------------------------------------
    // Dashboard
    // -------------------------------------------------------------------------

    public function getDashboard(User $viewer): array
    {
        return $this->ticketRepo->getDashboardStats($viewer);
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private function assertCanView(Ticket $ticket, User $viewer): void
    {
        if ($viewer->isAdmin()) return;

        if ($viewer->isTechnician() && $ticket->getTechnician()?->getId() === $viewer->getId()) return;

        if ($ticket->getRequester()->getId() === $viewer->getId()) return;

        throw new \RuntimeException('Acesso negado.', 403);
    }
}
