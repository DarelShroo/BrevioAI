import { http } from '@/services/http'
import type { ApiEnvelope } from '@/types/api'
import type {
  LoginData,
  LoginRequest,
  PasswordRecoveryData,
  PasswordRecoveryHandshakeRequest,
  PasswordRecoveryVerifyRequest,
  RegisterData,
  RegisterRequest,
  SessionData,
} from '@/types/auth'

export async function login(payload: LoginRequest): Promise<LoginData> {
  const { data } = await http.post<ApiEnvelope<LoginData>>('/auth/login', payload)
  return data.data
}

export async function register(payload: RegisterRequest): Promise<RegisterData> {
  const { data } = await http.post<ApiEnvelope<RegisterData>>('/auth/register', payload)
  return data.data
}

export async function refresh(): Promise<LoginData> {
  const { data } = await http.post<ApiEnvelope<LoginData>>('/auth/refresh')
  return data.data
}

export async function logout(): Promise<void> {
  await http.post('/auth/logout')
}

export async function getSession(): Promise<SessionData> {
  const { data } = await http.get<ApiEnvelope<SessionData>>('/auth/session')
  return data.data
}

export async function passwordRecoveryHandshake(
  payload: PasswordRecoveryHandshakeRequest,
): Promise<PasswordRecoveryData> {
  const { data } = await http.post<ApiEnvelope<PasswordRecoveryData>>(
    '/auth/password-recovery-handshake',
    payload,
  )
  return data.data
}

export async function passwordRecoveryVerify(
  payload: PasswordRecoveryVerifyRequest,
): Promise<PasswordRecoveryData> {
  const { data } = await http.post<ApiEnvelope<PasswordRecoveryData>>(
    '/auth/password-recovery-verify',
    payload,
  )
  return data.data
}
