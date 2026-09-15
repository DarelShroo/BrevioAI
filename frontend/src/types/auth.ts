export interface LoginRequest {
  identity: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface LoginData {
  authenticated: boolean
}

export interface RegisterData {
  folder: unknown
  authenticated: boolean
}

export interface SessionData {
  authenticated: boolean
  user_id?: string | null
}

export interface PasswordRecoveryHandshakeRequest {
  identity: string
}

export interface PasswordRecoveryVerifyRequest {
  email: string
  password: string
  otp: number
}

export interface PasswordRecoveryData {
  message: string
}
