<?php

declare(strict_types=1);

namespace App\Tests\Unit;

use App\Entity\User;
use App\Repository\UserRepository;
use App\Service\AuthService;
use Doctrine\ORM\EntityManagerInterface;
use PHPUnit\Framework\MockObject\MockObject;
use PHPUnit\Framework\TestCase;

/**
 * Testes unitários para AuthService.
 * Usa mocks de UserRepository e EntityManager — sem banco real.
 */
class AuthServiceTest extends TestCase
{
    private AuthService $authService;
    private UserRepository&MockObject $userRepo;
    private EntityManagerInterface&MockObject $em;

    protected function setUp(): void
    {
        $this->userRepo = $this->createMock(UserRepository::class);
        $this->em       = $this->createMock(EntityManagerInterface::class);

        $this->authService = new AuthService(
            $this->userRepo,
            $this->em,
            'test-secret-key-with-32-chars-ok',
            30,
        );
    }

    // -----------------------------------------------------------------------
    // Registro
    // -----------------------------------------------------------------------

    public function test_register_throws_when_email_exists(): void
    {
        $this->userRepo
            ->method('emailExists')
            ->willReturn(true);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('E-mail já cadastrado.');

        $this->authService->register('João', 'joao@teste.com', 'senha123');
    }

    public function test_register_persists_user_with_argon2_hash(): void
    {
        $this->userRepo->method('emailExists')->willReturn(false);

        $this->em->expects($this->once())->method('persist');
        $this->em->expects($this->once())->method('flush');

        $user = $this->authService->register('João', 'joao@teste.com', 'senha123');

        $this->assertSame('João', $user->getName());
        $this->assertTrue(
            password_verify('senha123', $user->getPasswordHash()),
            'Hash deve ser verificável com password_verify'
        );
        $this->assertStringStartsWith('$argon2', $user->getPasswordHash(), 'Deve usar Argon2ID');
    }

    // -----------------------------------------------------------------------
    // Login
    // -----------------------------------------------------------------------

    public function test_login_throws_when_user_not_found(): void
    {
        $this->userRepo->method('findByEmail')->willReturn(null);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('E-mail ou senha incorretos.');

        $this->authService->login('naoexiste@teste.com', 'qualquer');
    }

    public function test_login_throws_when_user_inactive(): void
    {
        $user = (new User())
            ->setName('Inativo')
            ->setEmail('inativo@teste.com')
            ->setPasswordHash(password_hash('senha', PASSWORD_ARGON2ID))
            ->setIsActive(false);

        $this->userRepo->method('findByEmail')->willReturn($user);

        $this->expectException(\RuntimeException::class);
        $this->authService->login('inativo@teste.com', 'senha');
    }

    public function test_login_throws_when_wrong_password(): void
    {
        $user = (new User())
            ->setName('Ativo')
            ->setEmail('ativo@teste.com')
            ->setPasswordHash(password_hash('correta', PASSWORD_ARGON2ID));

        $this->userRepo->method('findByEmail')->willReturn($user);

        $this->expectException(\RuntimeException::class);
        $this->expectExceptionMessage('E-mail ou senha incorretos.');

        $this->authService->login('ativo@teste.com', 'errada');
    }

    public function test_login_returns_token_on_success(): void
    {
        $user = (new User())
            ->setName('Herickson')
            ->setEmail('herickson@teste.com')
            ->setPasswordHash(password_hash('senha123', PASSWORD_ARGON2ID));

        $this->userRepo->method('findByEmail')->willReturn($user);

        $result = $this->authService->login('herickson@teste.com', 'senha123');

        $this->assertArrayHasKey('access_token', $result);
        $this->assertSame('bearer', $result['token_type']);
        $this->assertNotEmpty($result['access_token']);
    }

    // -----------------------------------------------------------------------
    // JWT
    // -----------------------------------------------------------------------

    public function test_generated_token_is_decodable(): void
    {
        $user = (new User())
            ->setName('Herickson')
            ->setEmail('herickson@teste.com')
            ->setPasswordHash('hash')
            ->setRole(User::ROLE_ADMIN);

        $token   = $this->authService->generateToken($user);
        $payload = $this->authService->decodeToken($token);

        $this->assertSame('ADMIN', $payload->role);
        $this->assertSame('herickson@teste.com', $payload->email);
    }

    public function test_decode_throws_on_invalid_token(): void
    {
        $this->expectException(\Exception::class);
        $this->authService->decodeToken('token.invalido.aqui');
    }

    // -----------------------------------------------------------------------
    // serializeUser
    // -----------------------------------------------------------------------

    public function test_serialize_user_excludes_password(): void
    {
        $user = (new User())
            ->setName('Ana')
            ->setEmail('ana@teste.com')
            ->setPasswordHash('hash-secreto');

        $data = $this->authService->serializeUser($user);

        $this->assertArrayNotHasKey('passwordHash', $data);
        $this->assertArrayNotHasKey('password', $data);
        $this->assertArrayHasKey('email', $data);
        $this->assertArrayHasKey('role', $data);
    }
}
