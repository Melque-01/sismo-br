---
description: Roda a suíte de testes do Sismos BR (unitários + integração opcional)
---

Verificação do Sismos BR. Siga na ordem.

1. Confirme que o diretório atual contém `app.py` e `tests\`. Se não contiver, pare e avise.
2. Se existir `.venv\Scripts\Activate.ps1`, ative antes de rodar Python.
3. Rode a suíte padrão:
   - `python -m unittest discover -s tests -v`
4. Se o pedido exigir banco (ou se a mudança tocar SQL/PostGIS), rode também:
   - `$env:SISMOS_TESTAR_DB=1; python -m unittest discover -s tests -v`
   - Os testes de banco são pulados por padrão; sem `SISMOS_TESTAR_DB=1` eles não provam nada.
5. Smoke local, se o servidor estiver no ar:
   - `try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/status -TimeoutSec 3).StatusCode } catch { "fora do ar" }`
6. Relate: total de testes, falhas, erros e pulados; diga explicitamente se os testes de banco rodaram ou não.

Sem commit, push, SSH (ver `docs/LOCAL_NOTAS.md`) ou deploy sem autorização explícita. Não alterar `SESSION_SECRET`, cookies ou hashing de senha para "facilitar teste".
