<?php

declare(strict_types=1);

namespace App\Service;

use App\Entity\User;
use App\Repository\UserRepository;
use Doctrine\ORM\EntityManagerInterface;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;

/**
 * Serviço de autenticação — equivalente ao app/core/security.py do projeto Python.
 * Responsável por hash de senha, geração e validação de JWT.
 */
class AuthService
{
    private string $jwtSecret;
    private int    $jwtExpireMinutes;

    public function __construct(
        private readonly UserRepository       $userRepository,
        private readonly EntityManagerInterface $em,
        string $jwtSecret,
        int    $jwtExpireMinutes = 30,
    ) {
        $this->jwtSecret        = $jwtSecret;
        $this->jwtExpireMinutes = $jwtExpireMinutes;
    }

    // -------------------------------------------------------------------------
    // Registro
    // -------------------------------------------------------------------------

    /**
     * Cria um novo usuário com senha em Argon2ID (equivalente ao pwdlib+Argon2 do Python).
     *
     * @throws \RuntimeException se o e-mail já estiver em uso
     */
    public function register(string $name, string $email, string $password): User
    {
        if ($this->userRepository->emailExists($email)) {
            throw new \RuntimeException('E-mail já cadastrado.', 409);
        }

        $user = (new User())
            ->setName(trim($name))
            ->setEmail($email)
            ->setPasswordHash(
                password_hash($password, PASSWORD_ARGON2ID)
            );

        $this->em->persist($user);
        $this->em->flush();

        return $user;
    }

    // -------------------------------------------------------------------------
    // Login
    // -------------------------------------------------------------------------

    /**
     * Valida credenciais e retorna o token JWT.
     *
     * @throws \RuntimeException se as credenciais forem inválidas
     */
    public function login(string $email, string $password): array
    {
        $user = $this->userRepository->findByEmail($email);

        if ($user === null || !$user->isActive()) {
            throw new \RuntimeException('E-mail ou senha incorretos.', 401);
        }

        if (!password_verify($password, $user->getPasswordHash())) {
            throw new \RuntimeException('E-mail ou senha incorretos.', 401);
        }

        return [
            'access_token' => $this->generateToken($user),
            'token_type'   => 'bearer',
            'user'         => $this->serializeUser($user),
        ];
    }

    // -------------------------------------------------------------------------
    // JWT
    // -------------------------------------------------------------------------

    /**
     * Gera um token JWT com os dados do usuário — equivalente ao create_access_token do Python.
     */
    public function generateToken(User $user): string
    {
        $now     = time();
        $payload = [
            'iss'   => 'helpdesk-api-php',
            'iat'   => $now,
            'exp'   => $now + ($this->jwtExpireMinutes * 60),
            'sub'   => (string) $user->getId(),
            'name'  => $user->getName(),
            'email' => $user->getEmail(),
            'role'  => $user->getRole(),
        ];

        return JWT::encode($payload, $this->jwtSecret, 'HS256');
    }

    /**
     * Decodifica e valida um token JWT. Lança exceção se inválido ou expirado.
     */
    public function decodeToken(string $token): object
    {
        return JWT::decode($token, new Key($this->jwtSecret, 'HS256'));
    }

    /**
     * Extrai o usuário autenticado do header Authorization: Bearer <token>.
     *
     * @throws \RuntimeException se o token estiver ausente ou inválido
     */
    public function getUserFromRequest(): User
    {
        $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';

        if (!preg_match('/^Bearer\s+(.+)$/i', $header, $m)) {
            throw new \RuntimeException('Token não fornecido.', 401);
        }

        try {
            $payload = $this->decodeToken($m[1]);
        } catch (\Exception) {
            throw new \RuntimeException('Token inválido ou expirado.', 401);
        }

        $user = $this->userRepository->find((int) $payload->sub);

        if ($user === null || !$user->isActive()) {
            throw new \RuntimeException('Usuário não encontrado ou inativo.', 401);
        }

        return $user;
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    public function serializeUser(User $user): array
    {
        return [
            'id'         => $user->getId(),
            'name'       => $user->getName(),
            'email'      => $user->getEmail(),
            'role'       => $user->getRole(),
            'is_active'  => $user->isActive(),
            'created_at' => $user->getCreatedAt()->format(\DateTimeInterface::ATOM),
        ];
    }
}
