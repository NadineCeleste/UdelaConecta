from pydantic import BaseModel


class Credenciales(BaseModel):
    email: str
    password: str


class SocialRequest(BaseModel):
    provider: str


class ResetPasswordRequest(BaseModel):
    email: str


class EmailRequest(BaseModel):
    email: str


class AsignarRequest(BaseModel):
    pasante_email: str
