# SITEC

Sistema de Inventário de Tecnologia da Escola Cabianca para controlar a disponibilidade e reserva de dispositivos por quantidade e faixa de horário.

## Rodar localmente

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`. Cadastre categorias, tipos e dispositivos pelo `/admin/`. Usuários autenticados criam reservas; administradores também podem cadastrar dispositivos e editar reservas de qualquer professor.

## Supabase e Vercel

Defina `SECRET_KEY`, `DATABASE_URL`, `DEBUG=False` e `ALLOWED_HOSTS` nas variáveis da Vercel. Para o Supabase, use a URL do pooler de transação na porta `6543`; o SSL é ativado automaticamente. Execute as migrações manualmente no ambiente configurado:

```powershell
python manage.py migrate
```

O arquivo `vercel.json` expõe `config/wsgi.py` como aplicação WSGI e o WhiteNoise serve os arquivos estáticos coletados.

## Testes

```powershell
python manage.py test reservas
```
