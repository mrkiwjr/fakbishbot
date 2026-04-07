interface TelegramWebApp {
  initData: string
  initDataUnsafe: {
    user?: {
      id: number
      first_name: string
      last_name?: string
      username?: string
    }
  }
}

interface Window {
  Telegram?: {
    WebApp?: TelegramWebApp
  }
}
