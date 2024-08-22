/*
 * This Runner for PM2
 */

module.exports = {
  apps: [
    {
        name: "Telegram-Api",
        script: "./venv/bin/uvicorn",
        args: "app.main:app",
        interpreter: "./venv/bin/python3",
        env: {
          APP_ENV: "production",
          SECRET_KEY: "your_secret_key"
        }
      }
  ]
}
