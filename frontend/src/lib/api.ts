import axios from "axios";
import { getToken } from "./auth";

const API = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
    headers: { "Content-Type": "application/json" },
});

API.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export interface Citation {
    section_id: string;
    title: string;
    source: string;
    source_type: string;
    score: number;
}

export interface QueryResponse {
    question: string;
    answer: string;
    chat_id?: string;
    citations: Citation[];
    context_used: number;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations: Citation[];
    timestamp: Date;
    loading?: boolean;
}

export interface Chat {
    id: string;
    title: string;
    messages: Message[];
    createdAt: Date;
}

interface ServerChat {
    id: string;
    title?: string | null;
    created_at: string;
}

interface ServerMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[] | null;
    created_at: string;
}

function toChat(chat: ServerChat, messages: Message[] = []): Chat {
    return {
        id: chat.id,
        title: chat.title || "New Chat",
        messages,
        createdAt: new Date(chat.created_at),
    };
}

function toMessage(message: ServerMessage): Message {
    return {
        id: message.id,
        role: message.role,
        content: message.content,
        citations: message.citations || [],
        timestamp: new Date(message.created_at),
    };
}

export async function askQuestion(
    question: string,
    chatId?: string
): Promise<QueryResponse> {
    const res = await API.post<QueryResponse>("/api/query", {
        question,
        chat_id: chatId,
        k_vector: 4,
        k_graph: 6,
    });
    return res.data;
}

export async function getChats(): Promise<Chat[]> {
    const res = await API.get<{ success: boolean; chats: ServerChat[] }>("/api/chats");
    return res.data.chats.map(chat => toChat(chat));
}

export async function getChat(chatId: string): Promise<Chat> {
    const res = await API.get<{
        success: boolean;
        chat: ServerChat;
        messages: ServerMessage[];
    }>(`/api/chats/${chatId}`);

    return toChat(
        res.data.chat,
        res.data.messages.map(toMessage),
    );
}

export async function createChat(title?: string): Promise<Chat> {
    const res = await API.post<{ success: boolean; chat: ServerChat }>(
        "/api/chats",
        { title: title || null },
    );
    return toChat(res.data.chat);
}

export async function deleteChat(chatId: string): Promise<void> {
    await API.delete(`/api/chats/${chatId}`);
}

export async function checkHealth(): Promise<{
    status: string;
    llm_status: string;
    total_vectors?: number;
    total_nodes?: number;
    total_edges?: number;
}> {
    const res = await API.get("/api/health");
    return res.data;
}

export function generateId(): string {
    return Math.random().toString(36).slice(2, 11);
}
