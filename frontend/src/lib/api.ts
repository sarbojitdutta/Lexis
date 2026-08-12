import axios from "axios";

const API = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
    headers: { "Content-Type": "application/json" },
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

export async function askQuestion(
    question: string
): Promise<QueryResponse> {
    const res = await API.post<QueryResponse>("/api/query", {
        question,
        k_vector: 4,
        k_graph: 6,
    });
    return res.data;
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

export function createChat(firstQuestion?: string): Chat {
    return {
        id: generateId(),
        title: firstQuestion
            ? firstQuestion.slice(0, 40) + (firstQuestion.length > 40 ? "..." : "")
            : "New Chat",
        messages: [],
        createdAt: new Date(),
    };
}