export class ApiError extends Error { constructor(message:string,public status:number){super(message);this.name='ApiError'} }
// During development Vite proxies /api to FastAPI so the browser uses a same-origin URL.
// A deployed frontend can set VITE_API_BASE_URL to the trusted HTTPS API origin.
export function createClient(token:string,base=import.meta.env.VITE_API_BASE_URL || '') {
  return async function request<T>(path:string,method='GET',body?:unknown,signal?:AbortSignal):Promise<T> {
    let response:Response;
    try {
      response=await fetch(`${base.replace(/\/$/,'')}/api${path}`,{method,signal,cache:'no-store',headers:{Authorization:`Bearer ${token}`,...(body!==undefined?{'Content-Type':'application/json'}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
    } catch(e) {
      if(e instanceof DOMException && e.name==='AbortError')throw e;
      throw new ApiError('Cannot reach your recovery service. Check that FastAPI is running.',0);
    }
    const payload=await response.json().catch(()=>null);
    if(!response.ok){
      const message=typeof payload?.error?.message==='string'?payload.error.message:
        typeof payload?.detail==='string'?payload.detail:
        Array.isArray(payload?.detail)?'Some fields were invalid. Please check the form.':
        `Request failed (${response.status}).`;
      throw new ApiError(message,response.status);
    }
    if(!payload || !('data' in payload))throw new ApiError('The service returned an unexpected response.',502);
    return payload.data as T;
  }
}
export type Client=ReturnType<typeof createClient>;
