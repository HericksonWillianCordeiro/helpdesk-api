<?php

declare(strict_types=1);

namespace App\Controller;

use App\Service\AuthService;
use App\Service\TicketService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Attribute\Route;
use App\Entity\Ticket;

#[Route('/api/tickets', name: 'ticket_')]
class TicketController extends AbstractController
{
    public function __construct(
        private readonly TicketService $ticketService,
        private readonly AuthService   $authService,
    ) {}

    /**
     * GET /api/tickets
     * Lista tickets com filtros e paginação — equivalente ao GET /tickets do Python.
     */
    #[Route('', name: 'list', methods: ['GET'])]
    public function list(Request $request): JsonResponse
    {
        try {
            $viewer  = $this->authService->getUserFromRequest();
            $filters = array_filter([
                'status'     => $request->query->get('status'),
                'priority'   => $request->query->get('priority'),
                'category'   => $request->query->get('category'),
                'technician' => $request->query->get('technician'),
            ]);

            $page  = max(1, (int) $request->query->get('page', 1));
            $limit = min(100, max(1, (int) $request->query->get('limit', 20)));

            $result = $this->ticketService->list($viewer, $filters, $page, $limit);

            return $this->json([
                'success' => true,
                'data'    => array_map([$this, 'serializeTicket'], $result['items']),
                'meta'    => [
                    'total' => $result['total'],
                    'page'  => $page,
                    'limit' => $limit,
                    'pages' => (int) ceil($result['total'] / $limit),
                ],
            ]);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * POST /api/tickets
     * Cria novo ticket — apenas usuários comuns.
     */
    #[Route('', name: 'create', methods: ['POST'])]
    public function create(Request $request): JsonResponse
    {
        try {
            $viewer = $this->authService->getUserFromRequest();

            if ($viewer->isAdmin() || $viewer->isTechnician()) {
                return $this->json(['success' => false, 'message' => 'Admins e técnicos não abrem tickets.'], 403);
            }

            $data   = json_decode($request->getContent(), true) ?? [];
            $errors = $this->validateTicketData($data);

            if (!empty($errors)) {
                return $this->json(['success' => false, 'errors' => $errors], 422);
            }

            $ticket = $this->ticketService->create($viewer, $data);

            return $this->json(['success' => true, 'data' => $this->serializeTicket($ticket)], 201);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * GET /api/tickets/{id}
     */
    #[Route('/{id}', name: 'get', methods: ['GET'], requirements: ['id' => '\d+'])]
    public function get(int $id): JsonResponse
    {
        try {
            $viewer = $this->authService->getUserFromRequest();
            $ticket = $this->ticketService->get($id, $viewer);
            return $this->json(['success' => true, 'data' => $this->serializeTicket($ticket)]);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * PATCH /api/tickets/{id}/status
     * Altera status — técnicos e admins.
     */
    #[Route('/{id}/status', name: 'status', methods: ['PATCH'], requirements: ['id' => '\d+'])]
    public function updateStatus(int $id, Request $request): JsonResponse
    {
        try {
            $viewer = $this->authService->getUserFromRequest();
            $data   = json_decode($request->getContent(), true) ?? [];

            if (empty($data['status']) || !in_array($data['status'], [
                Ticket::STATUS_OPEN, Ticket::STATUS_IN_PROGRESS,
                Ticket::STATUS_WAITING_USER, Ticket::STATUS_RESOLVED, Ticket::STATUS_CLOSED,
            ], true)) {
                return $this->json(['success' => false, 'message' => 'Status inválido.'], 422);
            }

            $ticket = $this->ticketService->updateStatus($id, $viewer, $data['status'], $data['note'] ?? null);
            return $this->json(['success' => true, 'data' => $this->serializeTicket($ticket)]);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * PATCH /api/tickets/{id}/assign
     * Atribui técnico — apenas admins.
     */
    #[Route('/{id}/assign', name: 'assign', methods: ['PATCH'], requirements: ['id' => '\d+'])]
    public function assign(int $id, Request $request): JsonResponse
    {
        try {
            $viewer = $this->authService->getUserFromRequest();
            $data   = json_decode($request->getContent(), true) ?? [];

            if (empty($data['technician_id'])) {
                return $this->json(['success' => false, 'message' => 'technician_id é obrigatório.'], 422);
            }

            $ticket = $this->ticketService->assign($id, $viewer, (int) $data['technician_id']);
            return $this->json(['success' => true, 'data' => $this->serializeTicket($ticket)]);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * DELETE /api/tickets/{id}
     * Remove ticket — apenas admins.
     */
    #[Route('/{id}', name: 'delete', methods: ['DELETE'], requirements: ['id' => '\d+'])]
    public function delete(int $id): JsonResponse
    {
        try {
            $viewer = $this->authService->getUserFromRequest();
            $this->ticketService->delete($id, $viewer);
            return $this->json(['success' => true, 'message' => 'Ticket removido.']);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * POST /api/tickets/{id}/comments
     */
    #[Route('/{id}/comments', name: 'comment', methods: ['POST'], requirements: ['id' => '\d+'])]
    public function addComment(int $id, Request $request): JsonResponse
    {
        try {
            $viewer  = $this->authService->getUserFromRequest();
            $data    = json_decode($request->getContent(), true) ?? [];
            $content = trim($data['content'] ?? '');

            if (strlen($content) < 2) {
                return $this->json(['success' => false, 'message' => 'Comentário muito curto.'], 422);
            }

            $comment = $this->ticketService->addComment($id, $viewer, $content);

            return $this->json(['success' => true, 'data' => [
                'id'         => $comment->getId(),
                'content'    => $comment->getContent(),
                'author'     => $comment->getAuthor()->getName(),
                'created_at' => $comment->getCreatedAt()->format(\DateTimeInterface::ATOM),
            ]], 201);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * GET /api/tickets/dashboard
     */
    #[Route('/dashboard', name: 'dashboard', methods: ['GET'])]
    public function dashboard(): JsonResponse
    {
        try {
            $viewer = $this->authService->getUserFromRequest();
            return $this->json(['success' => true, 'data' => $this->ticketService->getDashboard($viewer)]);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    // -------------------------------------------------------------------------

    private function serializeTicket(\App\Entity\Ticket $ticket): array
    {
        return [
            'id'           => $ticket->getId(),
            'title'        => $ticket->getTitle(),
            'description'  => $ticket->getDescription(),
            'status'       => $ticket->getStatus(),
            'priority'     => $ticket->getPriority(),
            'requester'    => ['id' => $ticket->getRequester()->getId(), 'name' => $ticket->getRequester()->getName()],
            'technician'   => $ticket->getTechnician() ? ['id' => $ticket->getTechnician()->getId(), 'name' => $ticket->getTechnician()->getName()] : null,
            'category'     => ['id' => $ticket->getCategory()->getId(), 'name' => $ticket->getCategory()->getName()],
            'sla_due_at'   => $ticket->getSlaDeadline()?->format(\DateTimeInterface::ATOM),
            'is_overdue'   => $ticket->isOverdue(),
            'resolved_at'  => $ticket->getResolvedAt()?->format(\DateTimeInterface::ATOM),
            'created_at'   => $ticket->getCreatedAt()->format(\DateTimeInterface::ATOM),
            'updated_at'   => $ticket->getUpdatedAt()->format(\DateTimeInterface::ATOM),
        ];
    }

    private function validateTicketData(array $data): array
    {
        $errors = [];
        if (empty($data['title']) || strlen(trim($data['title'])) < 3) {
            $errors['title'] = 'Título deve ter pelo menos 3 caracteres.';
        }
        if (empty($data['description'])) {
            $errors['description'] = 'Descrição é obrigatória.';
        }
        if (empty($data['category_id'])) {
            $errors['category_id'] = 'Categoria é obrigatória.';
        }
        if (isset($data['priority']) && !in_array($data['priority'], [
            Ticket::PRIORITY_LOW, Ticket::PRIORITY_MEDIUM,
            Ticket::PRIORITY_HIGH, Ticket::PRIORITY_CRITICAL,
        ], true)) {
            $errors['priority'] = 'Prioridade inválida.';
        }
        return $errors;
    }
}
