# Publicar en Render (link permanente)

1. Crea una cuenta en https://render.com (puedes entrar con GitHub).
2. **New → Blueprint** y elige el repositorio `YusTati27/sala-steam`. Render lee `render.yaml`.
3. Define también `ADMIN_SIGNUP_PIN`: con ese PIN cualquiera puede crearse como administrador desde el registro (casilla «Registrarme como administrador»). Cuando lo pida, escribe `BOOTSTRAP_ADMIN_EMAIL` (tu correo) y `BOOTSTRAP_ADMIN_PASSWORD` (una contraseña nueva, mín. 8 con letras y números).
4. Espera el build (varios minutos). El link queda como `https://sala-steam-xxxx.onrender.com`.

## Qué esperar (plan gratuito)
- El servicio se **duerme** tras ~15 min sin visitas; la primera carga tarda ~1 min.
- La base SQLite vive en el disco temporal: **al reiniciar o redeplegar se borra** (cuentas registradas incluidas). Al arrancar se
  regenera el simulador y se recrea el administrador con las variables de arriba.
- Para datos persistentes: crear una base PostgreSQL en Render y poner su URL como `DATABASE_URL`
  (`postgresql+psycopg://...`). El código es portable pero **no se ha probado contra PostgreSQL**.
- Cualquiera con el link puede registrarse como cliente y ver el simulador. El panel de administrador solo con las credenciales del paso 3.
