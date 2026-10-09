<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\TicketRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: TicketRepository::class)]
#[ORM\Table(name: 'tickets')]
#[ORM\HasLifecycleCallbacks]
class Ticket
{
    public const STATUS_OPEN         = 'OPEN';
    public const STATUS_IN_PROGRESS  = 'IN_PROGRESS';
    public const STATUS_WAITING_USER = 'WAITING_USER';
    public const STATUS_RESOLVED     = 'RESOLVED';
    public const STATUS_CLOSED       = 'CLOSED';

    public const PRIORITY_LOW      = 'LOW';
    public const PRIORITY_MEDIUM   = 'MEDIUM';
    public const PRIORITY_HIGH     = 'HIGH';
    public const PRIORITY_CRITICAL = 'CRITICAL';

    /** SLA em horas por prioridade (espelho do projeto Python) */
    public const SLA_HOURS = [
        self::PRIORITY_CRITICAL => 4,
        self::PRIORITY_HIGH     => 8,
        self::PRIORITY_MEDIUM   => 24,
        self::PRIORITY_LOW      => 72,
    ];

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 200)]
    private string $title;

    #[ORM\Column(type: 'text')]
    private string $description;

    #[ORM\Column(type: 'string', length: 20)]
    private string $status = self::STATUS_OPEN;

    #[ORM\Column(type: 'string', length: 10)]
    private string $priority = self::PRIORITY_MEDIUM;

    #[ORM\ManyToOne(targetEntity: User::class, inversedBy: 'tickets')]
    #[ORM\JoinColumn(nullable: false)]
    private User $requester;

    #[ORM\ManyToOne(targetEntity: User::class, inversedBy: 'assignedTickets')]
    #[ORM\JoinColumn(nullable: true)]
    private ?User $technician = null;

    #[ORM\ManyToOne(targetEntity: Category::class, inversedBy: 'tickets')]
    #[ORM\JoinColumn(nullable: false)]
    private Category $category;

    #[ORM\Column(type: 'datetime_immutable', nullable: true)]
    private ?\DateTimeImmutable $slaDeadline = null;

    #[ORM\Column(type: 'datetime_immutable', nullable: true)]
    private ?\DateTimeImmutable $resolvedAt = null;

    #[ORM\Column(type: 'datetime_immutable')]
    private \DateTimeImmutable $createdAt;

    #[ORM\Column(type: 'datetime_immutable')]
    private \DateTimeImmutable $updatedAt;

    #[ORM\OneToMany(targetEntity: TicketComment::class, mappedBy: 'ticket', cascade: ['remove'])]
    #[ORM\OrderBy(['createdAt' => 'ASC'])]
    private Collection $comments;

    public function __construct()
    {
        $this->comments  = new ArrayCollection();
        $this->createdAt = new \DateTimeImmutable();
        $this->updatedAt = new \DateTimeImmutable();
    }

    #[ORM\PreUpdate]
    public function onPreUpdate(): void
    {
        $this->updatedAt = new \DateTimeImmutable();
    }

    /** Calcula o prazo SLA com base na prioridade no momento da criação. */
    public function calculateSlaDeadline(): void
    {
        $hours = self::SLA_HOURS[$this->priority] ?? 24;
        $this->slaDeadline = $this->createdAt->modify("+{$hours} hours");
    }

    /** Indica se o ticket está atrasado em relação ao SLA. */
    public function isOverdue(): bool
    {
        if ($this->slaDeadline === null) return false;
        if (in_array($this->status, [self::STATUS_RESOLVED, self::STATUS_CLOSED], true)) return false;
        return new \DateTimeImmutable() > $this->slaDeadline;
    }

    // Getters / Setters
    public function getId(): ?int                         { return $this->id; }
    public function getTitle(): string                    { return $this->title; }
    public function setTitle(string $v): self             { $this->title = $v; return $this; }
    public function getDescription(): string              { return $this->description; }
    public function setDescription(string $v): self       { $this->description = $v; return $this; }
    public function getStatus(): string                   { return $this->status; }
    public function setStatus(string $v): self            { $this->status = $v; return $this; }
    public function getPriority(): string                 { return $this->priority; }
    public function setPriority(string $v): self          { $this->priority = $v; return $this; }
    public function getRequester(): User                  { return $this->requester; }
    public function setRequester(User $v): self           { $this->requester = $v; return $this; }
    public function getTechnician(): ?User                { return $this->technician; }
    public function setTechnician(?User $v): self         { $this->technician = $v; return $this; }
    public function getCategory(): Category               { return $this->category; }
    public function setCategory(Category $v): self        { $this->category = $v; return $this; }
    public function getSlaDeadline(): ?\DateTimeImmutable { return $this->slaDeadline; }
    public function getResolvedAt(): ?\DateTimeImmutable  { return $this->resolvedAt; }
    public function setResolvedAt(?\DateTimeImmutable $v): self { $this->resolvedAt = $v; return $this; }
    public function getCreatedAt(): \DateTimeImmutable    { return $this->createdAt; }
    public function getUpdatedAt(): \DateTimeImmutable    { return $this->updatedAt; }
    public function getComments(): Collection             { return $this->comments; }
}
