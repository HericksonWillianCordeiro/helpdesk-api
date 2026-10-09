<?php

declare(strict_types=1);

namespace App\Repository;

use App\Entity\Ticket;
use App\Entity\User;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<Ticket>
 */
class TicketRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Ticket::class);
    }

    /**
     * Lista tickets com filtros e paginação — espelho do GET /tickets do projeto Python.
     *
     * @return array{items: Ticket[], total: int}
     */
    public function findFiltered(
        User    $viewer,
        ?string $status     = null,
        ?string $priority   = null,
        ?int    $categoryId = null,
        ?int    $techId     = null,
        int     $page       = 1,
        int     $limit      = 20,
    ): array {
        $qb = $this->createQueryBuilder('t')
            ->leftJoin('t.requester',  'r')->addSelect('r')
            ->leftJoin('t.technician', 'tech')->addSelect('tech')
            ->leftJoin('t.category',   'c')->addSelect('c');

        // Escopo por papel
        if ($viewer->getRole() === User::ROLE_USER) {
            $qb->andWhere('t.requester = :viewer')->setParameter('viewer', $viewer);
        } elseif ($viewer->getRole() === User::ROLE_TECHNICIAN) {
            $qb->andWhere('t.technician = :viewer')->setParameter('viewer', $viewer);
        }

        if ($status !== null) {
            $qb->andWhere('t.status = :status')->setParameter('status', $status);
        }

        if ($priority !== null) {
            $qb->andWhere('t.priority = :priority')->setParameter('priority', $priority);
        }

        if ($categoryId !== null) {
            $qb->andWhere('c.id = :cat')->setParameter('cat', $categoryId);
        }

        if ($techId !== null && $viewer->isAdmin()) {
            $qb->andWhere('tech.id = :tech')->setParameter('tech', $techId);
        }

        $total = (int) (clone $qb)
            ->select('COUNT(t.id)')
            ->getQuery()
            ->getSingleScalarResult();

        $items = $qb
            ->orderBy('t.createdAt', 'DESC')
            ->setFirstResult(($page - 1) * $limit)
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();

        return ['items' => $items, 'total' => $total];
    }

    /** Estatísticas para o dashboard — equivalente ao GET /dashboard do Python. */
    public function getDashboardStats(User $viewer): array
    {
        $qb = $this->createQueryBuilder('t');

        if ($viewer->getRole() === User::ROLE_USER) {
            $qb->andWhere('t.requester = :viewer')->setParameter('viewer', $viewer);
        } elseif ($viewer->getRole() === User::ROLE_TECHNICIAN) {
            $qb->andWhere('t.technician = :viewer')->setParameter('viewer', $viewer);
        }

        $all = $qb->getQuery()->getResult();

        $now  = new \DateTimeImmutable();
        $stats = [
            'total'       => count($all),
            'open'        => 0,
            'in_progress' => 0,
            'resolved'    => 0,
            'critical'    => 0,
            'overdue'     => 0,
        ];

        foreach ($all as $ticket) {
            match ($ticket->getStatus()) {
                Ticket::STATUS_OPEN        => $stats['open']++,
                Ticket::STATUS_IN_PROGRESS => $stats['in_progress']++,
                Ticket::STATUS_RESOLVED    => $stats['resolved']++,
                default                    => null,
            };
            if ($ticket->getPriority() === Ticket::PRIORITY_CRITICAL) $stats['critical']++;
            if ($ticket->isOverdue()) $stats['overdue']++;
        }

        return $stats;
    }
}
