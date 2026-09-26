export type ChatSender = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  sender: ChatSender
  text: string
  imageUrls?: string[]
  createdAt: string
  loading?: boolean
  error?: boolean
}

export interface ChatComposerPayload {
  text: string
  images: File[]
}