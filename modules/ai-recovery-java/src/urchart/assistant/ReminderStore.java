package urchart.assistant;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.*;
import java.util.*;
/** Local fictional demonstration reminders. Replace with authenticated storage in production. */
public final class ReminderStore {
  private final Path file;
  private final Map<String,Reminder> items=new LinkedHashMap<>();
  public record Reminder(String id,String title,String notes,long nextAt,String zone,String repeat,boolean enabled) {
    Map<String,Object> json(){return Map.of("id",id,"title",title,"notes",notes,"nextAt",nextAt,"zone",zone,"repeat",repeat,"enabled",enabled);}
  }
  public ReminderStore(Path data) throws IOException {Files.createDirectories(data);file=data.resolve("assistant-reminders.tsv");if(Files.exists(file))for(String line:Files.readAllLines(file)){String[] a=line.split("\t",-1);if(a.length==7)try{Reminder r=new Reminder(a[0],dec(a[1]),dec(a[2]),Long.parseLong(a[3]),a[4],a[5],Boolean.parseBoolean(a[6]));items.put(r.id,r);}catch(RuntimeException ignored){}}}
  private static String enc(String t){return Base64.getUrlEncoder().encodeToString(t.getBytes(StandardCharsets.UTF_8));}
  private static String dec(String t){return new String(Base64.getUrlDecoder().decode(t),StandardCharsets.UTF_8);}
  private synchronized void save() throws IOException {List<String> l=new ArrayList<>();for(Reminder r:items.values())l.add(String.join("\t",r.id,enc(r.title),enc(r.notes),""+r.nextAt,r.zone,r.repeat,""+r.enabled));Path tmp=file.resolveSibling(file.getFileName()+".tmp");Files.write(tmp,l,StandardCharsets.UTF_8);try{Files.move(tmp,file,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}catch(AtomicMoveNotSupportedException e){Files.move(tmp,file,StandardCopyOption.REPLACE_EXISTING);}}
  public synchronized List<Map<String,Object>> list(){return items.values().stream().sorted(Comparator.comparingLong(Reminder::nextAt)).map(Reminder::json).toList();}
  public synchronized Reminder add(String title,String notes,long nextAt,String zone,String repeat) throws IOException {title=title.trim();if(title.isBlank()||title.length()>120)throw new IllegalArgumentException("Title required (max 120 characters)");if(notes.length()>500)throw new IllegalArgumentException("Notes too long");if(!Set.of("once","daily","weekly","weekdays","monthly").contains(repeat))throw new IllegalArgumentException("Invalid repeat schedule");try{ZoneId.of(zone);}catch(Exception e){throw new IllegalArgumentException("Invalid time zone");}if(nextAt<0||nextAt>System.currentTimeMillis()+315576000000L)throw new IllegalArgumentException("Invalid reminder time");Reminder r=new Reminder(UUID.randomUUID().toString(),title,notes,nextAt,zone,repeat,true);items.put(r.id,r);save();return r;}
  public synchronized Reminder action(String id,String action) throws IOException {Reminder r=items.get(id);if(r==null)throw new IllegalArgumentException("Reminder not found");if(action.equals("delete")){items.remove(id);save();return r;}Reminder updated;switch(action){case "complete"->{if(r.repeat.equals("once")){updated=new Reminder(r.id,r.title,r.notes,r.nextAt,r.zone,r.repeat,false);}else{ZonedDateTime z=Instant.ofEpochMilli(r.nextAt).atZone(ZoneId.of(r.zone));do{z=advance(z,r.repeat);}while(z.toInstant().toEpochMilli()<=System.currentTimeMillis());updated=new Reminder(r.id,r.title,r.notes,z.toInstant().toEpochMilli(),r.zone,r.repeat,true);}}case "snooze"->updated=new Reminder(r.id,r.title,r.notes,System.currentTimeMillis()+10*60_000L,r.zone,r.repeat,true);case "toggle"->updated=new Reminder(r.id,r.title,r.notes,r.nextAt,r.zone,r.repeat,!r.enabled);default->throw new IllegalArgumentException("Invalid action");}items.put(id,updated);save();return updated;}
  private static ZonedDateTime advance(ZonedDateTime z,String schedule){return switch(schedule){case "daily"->z.plusDays(1);case "weekly"->z.plusWeeks(1);case "monthly"->z.plusMonths(1);case "weekdays"->{do{z=z.plusDays(1);}while(z.getDayOfWeek()==DayOfWeek.SATURDAY||z.getDayOfWeek()==DayOfWeek.SUNDAY);yield z;}default->z.plusDays(1);};}
}
