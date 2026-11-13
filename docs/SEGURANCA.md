# Auditoria de segurança — 12/11/2026

Escopo: aplicação Sismos BR publicada em
`https://sismos-br.duckdns.org`, código local e servidor
`melque@<host-do-servidor>:2222`.

Método: revisão de código + Semgrep (12 rulesets) + testes dinâmicos na URL
pública + inspeção do servidor + `pip-audit`. Nenhum teste destrutivo; os testes
de rate limit bloquearam o login temporariamente e o app foi reiniciado depois.

## Resumo

| Severidade | Quantidade |
|---|---|
| Crítica | 0 |
| Alta | 3 |
| Média | 4 |
| Baixa | 6 |

Nenhuma injeção SQL, XSS refletido, path traversal ou acesso sem sessão foi
explorável. Os problemas graves são de configuração/abuso: HTTPS não forçado,
rate limit global e SSH com senha + sudo sem senha.

## Achados altos

### A1. Login funciona em HTTP e não há HSTS
- **Evidência:** `POST http://…/login` responde 303 e grava o cookie **sem
  `Secure`**. `http://…/login` responde 200, sem redirecionar para HTTPS. Não
  há `Strict-Transport-Security`.
- **Impacto:** quem digitar/for redirecionado para `http://` envia e-mail e
  senha em texto claro. O cookie de sessão também pode trafegar sem TLS.
- **Correção:** redirecionar para HTTPS quando `X-Forwarded-Proto: http`;
  adicionar HSTS; manter `Secure` no cookie (já ocorre em HTTPS).

### A2. Rate limit é global (um atacante bloqueia todos)
- **Evidência:** após 5 logins errados, o login correto respondeu **429**.
  O app usa `self.client_address[0]`; atrás do cloudflared, todo tráfego chega
  como `127.0.0.1`, então o limite é compartilhado por todos os usuários.
- **Impacto:** 5 requisições erradas bloqueiam o login de todo mundo por 5 min;
  10 cadastros inválidos bloqueiam novos cadastros por 1 h.
- **Correção:** usar `CF-Connecting-IP` (confiando apenas no túnel) como chave
  do limite; limitar também por conta/e-mail; aplicar backoff progressivo.

### A3. SSH aceita senha e `melque` tem sudo sem senha
- **Evidência:** `sshd -T` → `passwordauthentication yes`; `passwd -S melque`
  → `P` (senha definida); `sudo -n -l` → `(ALL) NOPASSWD: ALL`. `PermitRootLogin
  no` está correto.
- **Impacto:** se a senha for fraca (ou vazar), o atacante entra por SSH e vira
  root sem segunda barreira. O SSH está exposto na porta 2222.
- **Correção:** `PasswordAuthentication no`, `X11Forwarding no`,
  `AllowUsers melque`; remover `NOPASSWD` ou restringir os comandos; manter
  apenas chave, com senha forte na chave.

## Achados médios

### M1. Headers de segurança ausentes
- **Evidência:** `/login` e `/api/status` não enviam `Content-Security-Policy`,
  `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy` nem `Strict-Transport-Security`.
- **Impacto:** clickjacking (login em iframe), ausência de defesa em
  profundidade contra XSS, vazamento de URL de filtros no `Referer`.
- **Correção:** headers no `_enviar` (ou controller): `nosniff`, `DENY`,
  `no-referrer`, `Permissions-Policy` restritiva; CSP com nonce/hash; HSTS.

### M2. Cadastro aberto, sem verificação de e-mail e com enumeração
- **Evidência:** `/registrar` cria conta e já autentica; e-mail existente
  responde **409** (“já cadastrado”). Existem 2 contas no banco, uma delas
  `usuario@exemplo.com`, criada fora dos testes.
- **Impacto:** contas falsas/spam e descoberta de quais e-mails têm conta.
- **Correção:** verificação por e-mail ou código de convite; resposta genérica
  no cadastro; limite por e-mail além do IP.

### M3. Erros 500 devolvem detalhe interno
- **Evidência:** `app.py` responde
  `{"erro": "erro interno: <mensagem da exceção>"}`.
- **Impacto:** vazamento de caminhos, SQL e detalhes de infraestrutura.
- **Correção:** mensagem genérica ao cliente; log completo só no servidor.

### M4. Sem token CSRF em login/cadastro/logout
- **Evidência:** formulários não têm campo CSRF; `SameSite=Lax` é a única
  proteção. Login CSRF (forçar sessão do atacante) é possível em cenários
  específicos.
- **Impacto:** baixo/médio, dependente do navegador; logout CSRF é mitigado
  pelo `Lax`.
- **Correção:** token por sessão nos formulários; validar origem no POST.

## Achados baixos

| ID | Achado | Correção |
|---|---|---|
| B1 | `/api/status` é público e mostra contagens/última importação | exigir sessão ou reduzir o payload |
| B2 | `evento_id` do SISBRA usa MD5 | trocar por SHA-256 (exige reimportar) |
| B3 | Sessão stateless: logout não revoga token por 12 h | `jti` + lista de revogação ou TTL menor |
| B4 | Sem `Cache-Control: no-store` em login/API | adicionar no-store |
| B5 | `X11Forwarding yes`; 3 atualizações pendentes (apt, libapt, libpcre2) | desabilitar X11 e atualizar |
| B6 | Pacotes Docker instalados e inúteis no host | remover para reduzir superfície |

## Controles que passaram

- SQL injection: payloads em `ano_ini`, `uf`, `celula`, `lat`, `id` e `fonte`
  retornaram 400/404, sem erro SQL; consultas usam `%s`.
- XSS: e-mail com `<script>` foi escapado (`&lt;script&gt;`); saída HTML usa
  escape e o JS escapa dados do catálogo.
- Path traversal: `/static/../app.py` e variantes → 404/403.
- Sessão: token adulterado → 401; cookie com `HttpOnly`, `SameSite=Lax`,
  `Secure` em HTTPS, `Max-Age=43200`; sem `Domain`.
- Open redirect: `?next=https://example.com` continuou indo para `/`.
- Enumeração no login: mensagem genérica.
- Banco: PostgreSQL em `localhost`, `scram-sha-256`, SSL on; portas 5432 e
  8080 fechadas externamente; apenas 22 exposta.
- Segredos: `.env` modo 600; nenhum segredo real no Git (o `.env.vm` antigo
  tinha só placeholder); `pip-audit` sem vulnerabilidades conhecidas.
- Servidor: `PermitRootLogin no`; app roda como `melque`, não root.

## Semgrep

- 11 de 12 scans concluídos. `p/yaml` falhou por conflito include/exclude do
  runner no Windows; não foi possível avaliar o compose por esse ruleset.
- 5 achados brutos, 1 relevante: **MD5** em `servicos/catalogo.py:59` (B2).
- Falsos positivos prováveis: urllib com URL de configuração, porta do compose
  exposta (só desenvolvimento), imagem base não-distroless e “obfuscação” no
  gerador do PDF (base64 de fontes).
- SARIF: `static_analysis_semgrep_1/results/results.sarif`.

## Dependências

`pip-audit -r requirements.txt`: nenhuma vulnerabilidade conhecida (psycopg 3.3.8).

## Limitações

- Teste black-box, sem carga/DoS volumétrico, sem tentativa de roubo de token
  ou engenharia social.
- Não foi feita auditoria da conta Cloudflare, do host físico do container nem
  do histórico de pacotes do SO.
- O bloqueio de rate limit foi testado e revertido com restart; não é teste de
  resistência a ataque distribuído.

## Prioridade de correção

1. HTTPS obrigatório + HSTS + `Secure`.
2. Rate limit por `CF-Connecting-IP` + por conta.
3. SSH sem senha, sem X11 e sudo restrito.
4. Headers de segurança e CSP.
5. Erros genéricos, CSRF, verificação de e-mail.
6. Itens baixos e atualizações do SO.

## Correções aplicadas (12/11/2026)

- **A1 resolvido** — `app.py` responde 301 para HTTPS quando o proxy reporta
  `X-Forwarded-Proto: http`; HSTS (`max-age=31536000; includeSubDomains`) em
  respostas HTTPS. Commit `80055e2`.
- **A2 resolvido** — `app.py` aceita `X-Real-IP`/`X-Forwarded-For` **apenas**
  quando o peer é proxy confiável (`PROXIES_CONFIAVEIS`), cobrindo cloudflared
  e o nginx futuro; além disso, 10 falhas por e-mail em 15 minutos bloqueiam a
  conta mesmo vindas de IPs diferentes (`_FALHAS_CONTA` em `auth_controle.py`).
  Login correto zera o contador da conta. Os dicionários de tentativas têm teto
  (`LIMITE_CHAVES`) para não crescerem com e-mails aleatórios. Efeito colateral
  aceito: um atacante pode bloquear uma conta conhecida por 15 minutos.
- **A3 resolvido** — `PasswordAuthentication no`, `X11Forwarding no`,
  `AllowUsers melque` (drop-ins em `/etc/ssh/sshd_config.d/`, backup em
  `/home/melque/ssh-backup/`). O `NOPASSWD` do sudo foi mantido de propósito:
  `start_servidor.sh` precisa dele e o root do container não é o root do host.
- **M1 parcial** — `nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Permissions-Policy` e HSTS em todas as
  respostas. CSP ainda pendente (exige nonce/hash nos inline scripts).
- **M3 resolvido** — erro 500 genérico (`{"erro": "erro interno"}`); detalhe
  só no log do servidor.
- **M4 resolvido** — token CSRF de duplo envio (cookie `sismos_csrf` +
  `_csrf` nos formulários) em login, cadastro e logout; `hmac.compare_digest`
  na validação; POST sem token responde 403 e logout inválido não apaga a
  sessão.
- **B2 resolvido** — `evento_id` do SISBRA agora é SHA-256 (64 hex). A
  tabela foi reimportada (backup em `/home/melque/sismos_antes_b2.sql`);
  contagem inalterada: 5.044 SISBRA + 97 FDSN.
- **B4 resolvido** — `Cache-Control: no-store` em `/api/*`, `/login` e
  `/registrar`.
- **B5 parcial** — X11 desabilitado; upgrades de pacotes do SO pendentes.

Pendentes: M2 (verificação de e-mail/convite), B1 (`/api/status`),
B3 (revogação de sessão), B5 (upgrades), B6 (remover Docker do host), CSP.
