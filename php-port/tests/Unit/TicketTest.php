<?php

declare(strict_types=1);

namespace App\Tests\Unit;

use App\Entity\Category;
use App\Entity\Ticket;
use App\Entity\User;
use PHPUnit\Framework\TestCase;

/**
 * Testes unitários para a entidade Ticket.
 * Espelha o test_auth.py e test_tickets.py do projeto Python.
 */
class TicketTest extends TestCase
{
    private function makeUser(string $role = User::ROLE_USER): User
    {
        $user = new User();
        $user->setName('Teste')->setEmail('teste@teste.com')->setPasswordHash('hash')->setRole($role);
        return $user;
    }

    private function makeTicket(string $priority = Ticket::PRIORITY_HIGH): Ticket
    {
        $category = (new Category())->setName('Geral');
        $ticket   = (new Ticket())
            ->setTitle('Notebook não liga')
            ->setDescription('Equipamento não inicia')
            ->setPriority($priority)
            ->setRequester($this->makeUser())
            ->setCategory($category);
        return $ticket;
    }

    // -----------------------------------------------------------------------
    // Constantes e domínio
    // -----------------------------------------------------------------------

    public function test_status_constants_exist(): void
    {
        $this->assertSame('OPEN',         Ticket::STATUS_OPEN);
        $this->assertSame('IN_PROGRESS',  Ticket::STATUS_IN_PROGRESS);
        $this->assertSame('WAITING_USER', Ticket::STATUS_WAITING_USER);
        $this->assertSame('RESOLVED',     Ticket::STATUS_RESOLVED);
        $this->assertSame('CLOSED',       Ticket::STATUS_CLOSED);
    }

    public function test_priority_constants_exist(): void
    {
        $this->assertSame('LOW',      Ticket::PRIORITY_LOW);
        $this->assertSame('MEDIUM',   Ticket::PRIORITY_MEDIUM);
        $this->assertSame('HIGH',     Ticket::PRIORITY_HIGH);
        $this->assertSame('CRITICAL', Ticket::PRIORITY_CRITICAL);
    }

    public function test_sla_hours_defined_for_all_priorities(): void
    {
        foreach ([Ticket::PRIORITY_LOW, Ticket::PRIORITY_MEDIUM, Ticket::PRIORITY_HIGH, Ticket::PRIORITY_CRITICAL] as $p) {
            $this->assertArrayHasKey($p, Ticket::SLA_HOURS);
            $this->assertGreaterThan(0, Ticket::SLA_HOURS[$p]);
        }
    }

    public function test_critical_sla_is_less_than_high(): void
    {
        $this->assertLessThan(Ticket::SLA_HOURS[Ticket::PRIORITY_HIGH], Ticket::SLA_HOURS[Ticket::PRIORITY_CRITICAL]);
    }

    // -----------------------------------------------------------------------
    // SLA
    // -----------------------------------------------------------------------

    public function test_calculate_sla_deadline_sets_future_date(): void
    {
        $ticket = $this->makeTicket(Ticket::PRIORITY_HIGH);
        $ticket->calculateSlaDeadline();

        $this->assertNotNull($ticket->getSlaDeadline());
        $this->assertGreaterThan(new \DateTimeImmutable(), $ticket->getSlaDeadline());
    }

    public function test_is_overdue_false_for_new_ticket(): void
    {
        $ticket = $this->makeTicket(Ticket::PRIORITY_HIGH);
        $ticket->calculateSlaDeadline();

        $this->assertFalse($ticket->isOverdue());
    }

    public function test_is_overdue_false_when_resolved(): void
    {
        $ticket = $this->makeTicket(Ticket::PRIORITY_CRITICAL);
        $ticket->calculateSlaDeadline();
        $ticket->setStatus(Ticket::STATUS_RESOLVED);

        // Mesmo com prazo expirado, ticket resolvido não é "overdue"
        $this->assertFalse($ticket->isOverdue());
    }

    public function test_is_overdue_true_when_deadline_past(): void
    {
        $ticket  = $this->makeTicket(Ticket::PRIORITY_LOW);
        // Força um deadline no passado via reflexão
        $ref     = new \ReflectionProperty(Ticket::class, 'slaDeadline');
        $ref->setValue($ticket, new \DateTimeImmutable('-1 hour'));

        $this->assertTrue($ticket->isOverdue());
    }

    // -----------------------------------------------------------------------
    // Roles de usuário
    // -----------------------------------------------------------------------

    public function test_user_role_flags(): void
    {
        $user  = $this->makeUser(User::ROLE_USER);
        $tech  = $this->makeUser(User::ROLE_TECHNICIAN);
        $admin = $this->makeUser(User::ROLE_ADMIN);

        $this->assertFalse($user->isAdmin());
        $this->assertFalse($user->isTechnician());

        $this->assertTrue($tech->isTechnician());
        $this->assertFalse($tech->isAdmin());

        $this->assertTrue($admin->isAdmin());
        $this->assertFalse($admin->isTechnician());
    }

    // -----------------------------------------------------------------------
    // Estado inicial
    // -----------------------------------------------------------------------

    public function test_new_ticket_has_open_status(): void
    {
        $ticket = $this->makeTicket();
        $this->assertSame(Ticket::STATUS_OPEN, $ticket->getStatus());
    }

    public function test_new_ticket_has_no_technician(): void
    {
        $ticket = $this->makeTicket();
        $this->assertNull($ticket->getTechnician());
    }

    public function test_new_ticket_has_no_resolved_at(): void
    {
        $ticket = $this->makeTicket();
        $this->assertNull($ticket->getResolvedAt());
    }

    public function test_resolved_at_set_correctly(): void
    {
        $ticket = $this->makeTicket();
        $now    = new \DateTimeImmutable();
        $ticket->setResolvedAt($now);

        $this->assertSame($now, $ticket->getResolvedAt());
    }
}
