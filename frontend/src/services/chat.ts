import type {Client} from './client';
import type {Conversation,ChatReply} from '../types/api';
export const chatApi=(api:Client)=>({list:(offset=0)=>api<Conversation[]>(`/chat/conversations?limit=50&offset=${offset}`),get:(id:string)=>api<Conversation>(`/chat/conversations/${id}`),send:(message:string,id?:string)=>api<ChatReply>('/chat/message','POST',{message,...(id?{conversation_id:id}:{})})});
