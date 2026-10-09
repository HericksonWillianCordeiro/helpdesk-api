<?php

declare(strict_types=1);

namespace App\Controller;

use App\Service\AuthService;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/api/auth', name: 'auth_')]
class AuthController extends AbstractController
{
    public function __construct(private readonly AuthService $authService) {}

    /**
     * POST /api/auth/register
     * Equivalente ao POST /auth/register do projeto Python.
     */
    #[Route('/register', name: 'register', methods: ['POST'])]
    public function register(Request $request): JsonResponse
    {
        $data = json_decode($request->getContent(), true) ?? [];

        $errors = $this->validateRegister($data);
        if (!empty($errors)) {
            return $this->json(['success' => false, 'errors' => $errors], 422);
        }

        try {
            $user  = $this->authService->register($data['name'], $data['email'], $data['password']);
            $token = $this->authService->generateToken($user);

            return $this->json([
                'success'      => true,
                'access_token' => $token,
                'token_type'   => 'bearer',
                'user'         => $this->authService->serializeUser($user),
            ], 201);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 400);
        }
    }

    /**
     * POST /api/auth/login
     * Equivalente ao POST /auth/login (OAuth2 Password Bearer) do projeto Python.
     */
    #[Route('/login', name: 'login', methods: ['POST'])]
    public function login(Request $request): JsonResponse
    {
        $data = json_decode($request->getContent(), true) ?? [];

        if (empty($data['email']) || empty($data['password'])) {
            return $this->json(['success' => false, 'message' => 'E-mail e senha são obrigatórios.'], 422);
        }

        try {
            $result = $this->authService->login($data['email'], $data['password']);
            return $this->json(array_merge(['success' => true], $result));
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 401);
        }
    }

    /**
     * GET /api/auth/me
     * Retorna dados do usuário autenticado.
     */
    #[Route('/me', name: 'me', methods: ['GET'])]
    public function me(Request $request): JsonResponse
    {
        try {
            $user = $this->authService->getUserFromRequest();
            return $this->json(['success' => true, 'data' => $this->authService->serializeUser($user)]);
        } catch (\RuntimeException $e) {
            return $this->json(['success' => false, 'message' => $e->getMessage()], $e->getCode() ?: 401);
        }
    }

    // -------------------------------------------------------------------------

    private function validateRegister(array $data): array
    {
        $errors = [];
        if (empty($data['name']) || strlen(trim($data['name'])) < 2) {
            $errors['name'] = 'Nome deve ter pelo menos 2 caracteres.';
        }
        if (empty($data['email']) || !filter_var($data['email'], FILTER_VALIDATE_EMAIL)) {
            $errors['email'] = 'E-mail inválido.';
        }
        if (empty($data['password']) || strlen($data['password']) < 8) {
            $errors['password'] = 'Senha deve ter pelo menos 8 caracteres.';
        }
        return $errors;
    }
}
