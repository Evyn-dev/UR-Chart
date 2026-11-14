package urchart.assistant;
import com.sun.net.httpserver.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;
/** Mount this module under /api/assistant; does not own other teammates' endpoints. */
public final class AssistantModule {
  public interface PatientContextProvider {String patientContext();}
  private final ReminderStore reminders;
  private final AiClient ai=new AiClient();
  private final PatientContextProvider context;
  public AssistantModule(Path dataDir,PatientContextProvider provider) throws IOException {reminders=new ReminderStore(dataDir);context=provider;}
  public void register(HttpServer server){server.createContext("/api/assistant",this::handle);}
  private static final List<String> URGENT=List.of("severe chest pain","crushing chest pain","can't breathe","cant breathe","cannot breathe","difficulty breathing","severe shortness of breath","unconscious","passed out","fainted","face drooping","slurred speech","one side of my body is weak");
  private static final List<String> CONCERNS=List.of("incision","fever","swelling","dizzy","dizziness","bleeding","redness","chest pain","short of breath","trouble breathing","wound","palpitations");
  public void handle(HttpExchange x) throws IOException {try{
    String path=x.getRequestURI().getPath(),method=x.getRequestMethod();
    if(path.equals("/api/assistant/status")&&method.equals("GET")){send(x,200,Map.of("aiConfigured",ai.configured(),"demoMode",true,"contextContract","PatientContextProvider"));return;}
    if(path.equals("/api/assistant/chat")&&method.equals("POST")){chat(x);return;}
    if(path.equals("/api/assistant/reminders")){if(method.equals("GET")){send(x,200,Map.of("reminders",reminders.list(),"serverTime",System.currentTimeMillis()));return;}if(method.equals("POST")){Map<String,Object> v=body(x);ReminderStore.Reminder r=reminders.add(Json.str(v.get("title")),Json.str(v.get("notes")),number(v.get("nextAt")),Json.str(v.getOrDefault("zone","America/New_York")),Json.str(v.getOrDefault("repeat","once")));send(x,201,Map.of("reminder",r.json()));return;}}
    if(path.startsWith("/api/assistant/reminders/")&&method.equals("POST")){String id=path.substring("/api/assistant/reminders/".length());Map<String,Object> v=body(x);ReminderStore.Reminder r=reminders.action(id,Json.str(v.get("action")));send(x,200,Map.of("reminder",r.json(),"ok",true));return;}
    send(x,404,Map.of("error","Unknown assistant route"));
  }catch(IllegalArgumentException e){send(x,400,Map.of("error",e.getMessage()));}catch(Exception e){System.err.println("Assistant error: "+e.getClass().getSimpleName());send(x,503,Map.of("error","Assistant temporarily unavailable"));}}
  private void chat(HttpExchange x) throws IOException {Map<String,Object> v=body(x);String message=Json.str(v.get("message")).trim();if(message.isBlank()||message.length()>1500)throw new IllegalArgumentException("Message must be 1–1500 characters");String lower=message.toLowerCase(Locale.ROOT).replace('’','\'');for(String trigger:URGENT)if(lower.contains(trigger)){send(x,200,Map.of("risk","emergency","reply","This may be a medical emergency. Call 911 now in the US, or your local emergency number. Do not wait for UR Chart."));return;}for(String trigger:CONCERNS)if(lower.contains(trigger)){send(x,200,Map.of("risk","concern","reply","This symptom may require prompt medical attention. Contact your surgical care team now. For severe or rapidly worsening symptoms, call emergency services."));return;}
    String msg;
    if(!ai.configured()){msg="I'm Chart, your recovery companion. I can help organize reminders and answer questions once an AI key is configured on the Java server. For medical guidance, follow your actual discharge plan or contact your care team.";}
    else {try{msg=ai.reply(message,context.patientContext());}catch(Exception e){System.err.println("AI request failed: "+e.getClass().getSimpleName());msg="My AI connection is unavailable right now. Your reminders remain accessible, but for medical questions please use your discharge instructions or contact your care team.";}}
    send(x,200,Map.of("risk","routine","reply",msg,"mode",ai.configured()?"ai-or-fallback":"demo"));
  }
  private static long number(Object v){try{return (long)Double.parseDouble(Json.str(v));}catch(Exception e){throw new IllegalArgumentException("Invalid reminder date/time");}}
  private static Map<String,Object> body(HttpExchange x) throws IOException {byte[] bytes=x.getRequestBody().readNBytes(16385);if(bytes.length>16384)throw new IllegalArgumentException("Request too large");return Json.object(new String(bytes,StandardCharsets.UTF_8));}
  private static void send(HttpExchange x,int status,Object data) throws IOException {byte[] b=Json.stringify(data).getBytes(StandardCharsets.UTF_8);x.getResponseHeaders().set("Content-Type","application/json; charset=utf-8");x.getResponseHeaders().set("Cache-Control","no-store");x.sendResponseHeaders(status,b.length);try(OutputStream out=x.getResponseBody()){out.write(b);}}
}
