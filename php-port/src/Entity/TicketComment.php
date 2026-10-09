<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\TicketCommentRepository;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: TicketCommentRepository::class)]
#[ORM\Table(name: 'ticket_comments')]
class TicketComment
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Ticket::class, inversedBy: 'comments')]
    #[ORM\JoinColumn(nullable: false, onDelete: 'CASCADE')]
    private Ticket $ticket;

    #[ORM\ManyToOne(targetEntity: User::class)]
    #[ORM\JoinColumn(nullable: false)]
    private User $author;

    #[ORM\Column(type: 'text')]
    private string $content;

    #[ORM\Column(type: 'datetime_immutable')]
    private \DateTimeImmutable $createdAt;

    public function __construct()
    {
        $this->createdAt = new \DateTimeImmutable();
    }

    public function getId(): ?int                      { return $this->id; }
    public function getTicket(): Ticket                { return $this->ticket; }
    public function setTicket(Ticket $t): self         { $this->ticket = $t; return $this; }
    public function getAuthor(): User                  { return $this->author; }
    public function setAuthor(User $u): self           { $this->author = $u; return $this; }
    public function getContent(): string               { return $this->content; }
    public function setContent(string $c): self        { $this->content = $c; return $this; }
    public function getCreatedAt(): \DateTimeImmutable { return $this->createdAt; }
}
