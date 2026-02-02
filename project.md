# Projekt-Spezifikation: Interactive DJ Library Manager (CLI Edition)

## 1. Projektziel

Entwicklung eines modularen, interaktiven Python-CLI-Tools (Command Line Interface), das den Nutzer durch die Wartung seiner Musikbibliothek führt. Das Tool darf **keine destruktiven Aktionen** (Löschen, Verschieben) ohne explizite Bestätigung oder klare Konfiguration durchführen. Es dient als "Zentrale", um Duplikate zu bereinigen, korrupte Dateien zu isolieren und Playlists aus Spotify-Daten zu generieren.

## 2. User Experience (UX) & Workflow

Das Tool startet in einem **Hauptmenü** und bietet dem Nutzer Optionen an. Es nutzt Bibliotheken wie `rich` oder `questionary` für eine professionelle Darstellung (farbige Outputs, Tabellen, Fortschrittsbalken).

**Start-Screen:**

```text
=== DJ LIBRARY MASTER TOOL ===
Root Directory: /Volumes/MY_USB

[1] Scan & Deduplicate (Find & Remove Duplicates)
[2] Health Check (Find Corrupt FLACs)
[3] Playlist Sync (CSV to M3U)
[4] Full Auto-Mode (Run 1, 2, and 3 sequentially)
[q] Quit

```

---

## 3. Funktionale Module (Detailliert)

### Modul A: Der "Interactive Cleaner" (Deduplizierung)

**Workflow:**

1. **Scan:** Das Tool scannt rekursiv alle Dateien und berechnet Hash-Werte (SHA-256/MD5).
* *UI:* Fortschrittsbalken (`tqdm` oder `rich.progress`) anzeigen.


2. **Report:** Nach dem Scan wird eine Zusammenfassung angezeigt:
* *"Gefundene Dateien: 12.000"*
* *"Gefundene Duplikate: 450 (Belegter Speicher: 3.5 GB)"*


3. **Interaktion:** Der Nutzer wird gefragt:
* `[?] Wie sollen Duplikate behandelt werden?`
* `a) Löschen (Behalte erste gefundene Version)`
* `b) Verschieben in "/_DUPLICATES_TRASH"`
* `c) Nur Report anzeigen (keine Aktion)`
* `d) Abbrechen`




4. **Ausführung:** Erst nach Auswahl führt das Skript die Operation aus.

### Modul B: Der "Health Guard" (Integritätsprüfung)

**Workflow:**

1. **Scan:** Das Tool prüft alle FLAC-Dateien auf Dekodierbarkeit (`soundfile` / `flac -t`).
* *UI:* Fortschrittsbalken ist zwingend, da dieser Schritt rechenintensiv ist.


2. **Live-Log:** Fehlerhafte Dateien werden sofort rot im Terminal markiert:
* `[ERROR] Track A.flac ist korrupt (MD5 Checksum Failed).`


3. **Report & Entscheidung:**
* *"Scan abgeschlossen. 5 korrupte Dateien gefunden."*
* `[?] Aktion wählen:`
* `a) Dateien in Quarantäne verschieben (/_CORRUPT_FILES)`
* `b) Nichts tun`




4. **Dokumentation:** Unabhängig von der Auswahl wird **immer** eine CSV erstellt (`corrupt_files_report.csv`), damit der Nutzer weiß, welche Songs er neu herunterladen muss.

### Modul C: Der "Matchmaker" (Playlist Builder)

**Workflow:**

1. **Input:** Der Nutzer wird nach dem Pfad zur CSV-Datei gefragt.
* `[?] Pfad zur Exportify-CSV eingeben (Drag & Drop möglich): `


2. **Matching:** Das Tool führt das Fuzzy-Matching gegen die (bereinigte) Library durch.
3. **Review:** Anzeige einer Statistik vor dem Schreiben:
* *"Playlist: Party_2024"*
* *"Gefunden: 98 Tracks"*
* *"Fehlend: 2 Tracks (Siehe missing.txt)"*


4. **Export:**
* `[?] Playlist speichern als "Import_to_Rekordbox.m3u8"? [y/n]`



---

## 4. Technische Anforderungen

### 4.1. Tech Stack

* **Sprache:** Python 3.9+
* **Empfohlene Bibliotheken für CLI/UI:**
* `rich`: Für Tabellen, farbigen Text, Panels und schöne Progress-Bars (Essenziell für die "Profi-Optik").
* `questionary` oder `inquirer`: Für die Auswahlmenüs (Pfeiltasten-Bedienung statt nur Text-Input).


* **Core Logic:** `pandas`, `thefuzz`, `hashlib`, `soundfile`.

### 4.2. Konfiguration & Robustheit

* **Start-Argumente:** Das Skript sollte Argumente akzeptieren, um Pfade vorzugeben, aber interaktiv bleiben, wenn keine angegeben sind.
* `python master_tool.py --root "/Volumes/USB"`


* **Safety-Lock:** Ein globaler "Dry-Run" Modus (Simulationsmodus) sollte als Flag verfügbar sein (`--dry-run`), bei dem das Skript so tut, als ob es löscht/verschiebt, es aber nur loggt.

### 4.3. Pfad-Handling

* Das Tool muss mit **Leerzeichen** und **Sonderzeichen** in Pfaden umgehen können (besonders auf macOS Volumes).
* M3U-Export muss **absolute Pfade** verwenden, damit Rekordbox sie importieren kann, egal wo die M3U liegt.

---

## 5. Abgabe-Paket (Deliverables)

Das Team liefert folgende Komponenten:

1. **`dj_manager.py`**: Das Hauptskript mit dem interaktiven Menü.
2. **`modules/`**: Ordner mit den Untermodulen (`cleaner.py`, `doctor.py`, `matcher.py`) für sauberen Code.
3. **`requirements.txt`**: Enthält `rich`, `pandas`, `thefuzz`, `soundfile`, `questionary`.
4. **`README.md`**:
* Anleitung zur Installation (pip install -r requirements.txt).
* Erklärung, wie man `ffmpeg` oder `flac` installiert (Systemabhängigkeit für FLAC-Prüfung).



---

### Beispiel für die gewünschte Terminal-Ausgabe (Mockup):

```text
  _   _   _   _   _   _   _  
 / \ / \ / \ / \ / \ / \ / \ 
( D | J | M | A | S | T | E | R )
 \_/ \_/ \_/ \_/ \_/ \_/ \_/ 

>> Root Path detected: /Volumes/INTENSO

? Was möchtest du tun? (Use arrow keys)
 » 1. Duplikate suchen und bereinigen
   2. FLAC-Dateien auf Fehler prüfen
   3. Spotify-Playlist importieren
   4. Beenden

```
