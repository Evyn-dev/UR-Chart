import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.file.*;
import java.io.*;
import urchart.assistant.AssistantModule;

/** Independent Java demo. Does not replace the team's existing backend. */
public final class Launcher {
  public static void main(String[] args) throws Exception {
    int port=Integer.parseInt(System.getenv().getOrDefault("UR_CHART_JAVA_PORT","5055"));
    HttpServer server=HttpServer.create(new InetSocketAddress("127.0.0.1",port),0);
    new AssistantModule(Path.of("data"),()->"Synthetic demonstration profile only. No verified patient instructions or medical records are connected.").register(server);
    server.createContext("/",exchange->{
      String path=exchange.getRequestURI().getPath();
      String file=path.equals("/")?"index.html":path.substring(1);
      if(!file.equals("index.html")){exchange.sendResponseHeaders(404,-1);exchange.close();return;}
      byte[] bytes=Files.readAllBytes(Path.of("static/index.html"));
      exchange.getResponseHeaders().set("Content-Type","text/html; charset=utf-8");
      exchange.sendResponseHeaders(200,bytes.length);
      try(OutputStream out=exchange.getResponseBody()){out.write(bytes);}
    });
    server.start();
    System.out.printf("UR Chart AI demo: http://127.0.0.1:%d%n",port);
  }
}
