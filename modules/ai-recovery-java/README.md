# UR Chart: AI Recovery Assistant (Java module)

This **standalone feature module** belongs to the team UR Chart project. It is isolated under `modules/ai-recovery-java/` so the existing Python/FastAPI backend, database, and teammates' code are not overwritten.

## Run the Java 17+ demonstration

From `modules/ai-recovery-java`:

```powershell
mkdir out
javac -encoding UTF-8 -d out src/urchart/assistant/*.java Launcher.java
java -cp out Launcher
```

Visit http://127.0.0.1:5055. The server binds to the local computer only. Optionally set `OPENAI_API_KEY` as a server-side environment variable to enable responses through the OpenAI Responses API. Never commit the key. The default is explicit demo mode. `OPENAI_MODEL` and `UR_CHART_JAVA_PORT` are optional.

## Module scope

- Conversational AI entry point: `POST /api/assistant/chat` with JSON `{"message":"..."}`
- AI configuration status: `GET /api/assistant/status`
- Reminder list: `GET /api/assistant/reminders`
- Create reminder: `POST /api/assistant/reminders` with `title`, `notes`, `nextAt` (Unix milliseconds), `zone` (IANA), `repeat` (once/daily/weekdays/weekly/monthly)
- Reminder action: `POST /api/assistant/reminders/{id}` with `{"action":"complete"}`, `snooze`, `toggle`, or `delete`
- Browser speech recognition: **Chart Chart** wakes assistant; **Chart Emergency** immediately opens *demo* emergency panel.
- Spoken responses, location-on-permission, reminder browser notifications (only while site and server are running).

## Teammate integration contract

`AssistantModule` offers `PatientContextProvider`: implement `String patientContext()` using approved, authenticated records from your shared backend. Current standalone launcher deliberately supplies only synthetic placeholder context. **Do not copy patient data without permission.** The Java module is not yet connected to the existing Python/FastAPI service, shared tokens, or database. A future integration should authenticate users and fetch permitted data from the team's APIs or use a separately negotiated service contract. The current reminder store is a single-user local demo, **not production or multi-patient storage**.

## Medical and security limits

This is an educational hackathon demo, not a medical device. The keyword safety screen is incomplete and cannot determine clinical urgency reliably. **Emergency calls are never placed automatically**; in the USA patients should manually call 911 for an actual emergency. The geolocation field does not send coordinates to dispatchers. Browser wake detection is not always-on while locked/closed, and reminders are not delivered with the browser closed. Real patient data, actual 24/7 service, verified care instructions, authentication, clinical validation, notification infrastructure, and deployment remain out of scope. Use fictional data only.
