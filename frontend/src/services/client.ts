export class ApiError extends Error { constructor(message:string,public status:number){super(message);this.name='ApiError'} }
// Same-origin /api requests work with Vite's local proxy and Vercel's
// public /api -> backend service rewrite. Service binding URLs are server-only
// runtime values and must never be embedded in a browser bundle.
export function createClient(token:string,base='') {
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
