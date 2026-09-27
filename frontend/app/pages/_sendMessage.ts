import type { Ref } from 'vue'
import type { ChatComposerPayload, ChatMessage } from '~/types/chat'

type ChatActionsOptions = {
	messages: Ref<ChatMessage[]>
	imageError: Ref<string>
	conversationId: string
	chatEndpoint: string
}

type ChatResponse = {
	message?: { text?: string } | string
	text?: string
}

function createId() {
	return crypto.randomUUID()
}

function addImageUrls(files: File[]) {
	return files.map((file) => URL.createObjectURL(file))
}

export function createChatActions(options: ChatActionsOptions) {
	async function sendMessage(payload: ChatComposerPayload) {
		options.imageError.value = ''

		const userMessage: ChatMessage = {
			id: createId(),
			sender: 'user',
			text: payload.text,
			imageUrls: addImageUrls(payload.images),
			createdAt: new Date().toISOString()
		}
		const loadingId = createId()

		options.messages.value.push(userMessage, {
			id: loadingId,
			sender: 'assistant',
			text: '',
			createdAt: new Date().toISOString(),
			loading: true
		})

		if (!options.chatEndpoint) {
			options.messages.value = options.messages.value.map((message) => message.id === loadingId
				? { ...message, loading: false, error: true, text: '' }
				: message)
			return
		}

		try {
			const formData = new FormData()
			formData.append('conversationId', options.conversationId)
			formData.append('text', payload.text)
			payload.images.forEach((file) => formData.append('images', file))

			const response = await $fetch<ChatResponse>(options.chatEndpoint, {
				method: 'POST',
				body: formData
			})
			const responseText = typeof response.message === 'string'
				? response.message
				: response.message?.text ?? response.text ?? ''

			options.messages.value = options.messages.value.map((message) => message.id === loadingId
				? { ...message, loading: false, text: responseText }
				: message)
		} catch {
			options.messages.value = options.messages.value.map((message) => message.id === loadingId
				? { ...message, loading: false, error: true }
				: message)
		}
	}

	async function loadHistory() {
		if (!options.chatEndpoint) return

		const history = await $fetch<ChatMessage[]>(`${options.chatEndpoint}/history`, {
			query: { conversationId: options.conversationId }
		})
		options.messages.value = history
	}

	function cleanup() {
		options.messages.value
			.flatMap((message) => message.imageUrls ?? [])
			.forEach((url) => URL.revokeObjectURL(url))
	}

	return { sendMessage, loadHistory, cleanup }
}
