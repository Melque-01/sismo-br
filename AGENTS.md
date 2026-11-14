# Sismos BR — Regras para agentes

## Antes de alterar

- Ler `README.md`.
- Rodar `python -m unittest discover -s tests -v` antes e depois; se tocar SQL/PostGIS, com `SISMOS_TESTAR_DB=1`.
- Bug: reproduzir em teste que falha antes de corrigir.

## Revisão

- Antes de commit: `code-reviewer` no `git diff`.
- Mudou auth, sessão, SQL, filtros ou deploy? `security-reviewer` também.
- Revisores são somente leitura.

## Segurança

- Senha continua PBKDF2; não trocar hash nem afrouxar parâmetros.
- `SESSION_SECRET` obrigatório fora do local; cookie assinado com `HttpOnly`, `SameSite=Lax` e `Secure` quando HTTPS.
- SQL parametrizado; filtros (UF, magnitude, profundidade, período) validados no servidor.
- Erro sem stack trace ou PII.
- Importação não pode executar código do catálogo nem confiar no arquivo baixado.

## Deploy

- SSH `<host-do-servidor>:2222`; sem deploy ou restart sem autorização.
- Backup do Postgres antes de migração ou importação grande.
