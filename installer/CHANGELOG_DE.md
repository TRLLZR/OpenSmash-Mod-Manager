# 3.7.0

- Neue transparente Wortmarke und eigenes Symbol mit Windows-ICO-Auflösungen.
- Vollständige Darstellung der Wortmarke ohne alten festen Bildausschnitt.
- Bereinigtes GitHub-Quellpaket, englische Start-README und Beitragsanleitung.
- Inventarprüfung, Lizenz-/Herkunftsdokumentation und Windows-CI-Konfiguration.
- Historische Fallprotokolle und lokale Hilfsprogramme bleiben außerhalb der Veröffentlichung.
- Bestehende Bibliothek und Laufzeitintegration bleiben erhalten.

# 3.6.0

- Alle Downloads gemeinsam löschen; aktive Transfers werden sicher abgebrochen.
- 7z direkt importieren, verschachteln und über GameBanana/Manager-Links laden.
- Öffentliche andere Formate als „Nur Download“ laden und explizit speichern.
- Neue Entdecken-Details beginnen immer oben.
- Offizieller portabler 7-Zip-Decoder 26.05 mit Herkunft, Lizenz und Quellangebot.
- Erneuter Abgleich der Paketmeldungen; isolierter echter Jotaro-Download geprüft.
- CSK 6.0.0 bleibt mangels öffentlichem passendem Download offen.

# 3.5.0 – 02.11.2026

Stabile Downloadzeilen, weniger Leerlaufabfragen und teilbare JSON-Modlisten.
Fehlende Originaldateien werden nach Bestätigung heruntergeladen und installiert;
Konflikte bleiben pausiert, vorhandene Aktivierung erhalten. Stapel-Downloadbutton
verständlich benannt und nur bei Mehrfachauswahl. Inkompatible Frameworks werden
vor der Übersetzung erkannt, unveränderte Plugin-Sätze bei Asset-Änderungen
wiederverwendet.

# 3.4.0 – 02.11.2026

Liste/Kacheln mit gespeicherter Ansicht, kleine Mod-Titelbilder und eigene Bildauswahl. Fertige Downloads samt Archiv entfernbar, installierte Mods bleiben erhalten. Strukturabhängige Gameplay-Bibliotheksprüfung, vollständige dreistellige Kostümslots und klare Versionsfehler. Shadow bleibt wegen fehlender kompatibler CSK-Bibliothek für 13.0.5 unbestätigt.

# 3.3.0 – 02.11.2026

Einheitliche runde Buttons in Hauptansicht und Dialogen, einfachere Details, automatische Windows-Anzeigesprache mit 16 Sprachfamilien und dokumentierter Übersetzungsabdeckung. Python 3.14.10, erweiterte Windows-Archivpfadprüfung, Sicherheitsabgleich und englische Architektur-/Build-Dokumentation.

# 3.2.0 – Charakterfilter, Vollbild und Manager-Links

- Echte GameBanana-Skin-Unterkategorien als Charakterfilter mit Sortierung und Seiten.
- Detailbilder per Klick im Vollbild mit Bildwechsel und Esc.
- Eigenes benutzerbezogenes opensmashmm:-Protokoll, Uebergabe an laufenden Manager, Link oeffnen/kopieren. Oeffentliche Anbieter-Dateien werden ueber den bisherigen Downloadpfad geprueft.

# 3.1.0 – Übersichtliches Layout und deckende Oberfläche

- Neue Wortmarke ersetzt das bisherige Symbol und die zusätzliche Überschrift im Hauptfenster. Das Originalbild bleibt unverändert; nur seine transparenten Ränder werden in der Anzeige ausgespart.
- Vollständig deckende Hell-/Dunkel-/Systemdarstellung. Kein Desktop-Blur, keine Glasoptionen, kein Vordergrund-Schalter.
- Schmale Importleiste statt großer Ablagefläche; breitere Bibliothek und klar getrennte Navigation.
- Export, Gruppenaktionen, Vollprüfung, Updateprüfung und Protokolle unter Mehr. Kurzer Spielordnername mit vollständigem Pfad im Tooltip.
- Installations- und Konfliktaktionen werden passend zum aktuellen Schritt eingeblendet; Downloadaktionen brauchen eine geeignete Auswahl.
- Weniger wiederholte Hilfs-/Status-/Techniktexte; Bildnavigation nur bei vorhandenen Bildern. Normale Tastaturkürzel bleiben erhalten.
- Bestehende Mod-, Download-, Audio- und Sicherheitslogik unverändert.

# 3.0.0 – Inkrementelle Profile, Startton und GameBanana

- Persistente Herkunfts-, Aktivierungs-, Validierungs- und Konfliktübersicht; gleiche Kostümslots als vorsichtiger Kombinationshinweis.
- SQLite-Index für Metadaten und unveränderte Prüfsummen; nur betroffene Moddateien prüfen und bereitstellen. Unveränderte Verzeichnisse werden atomar weiterverwendet.
- NRO-Laufzeiten anhand tatsächlicher Plugin-/Plugin-Konfiguration cachen. Eine reine Skin-config.json löst keine erneute Plugin-Übersetzung aus.
- Entfernen verschiebt Moddaten in eine verwaltete Rückgängig-Ablage. Dauerhaftes Transaktionsjournal und Wiederherstellung nach Prozessabbruch.
- Schnelle Checkbox-Rückmeldung, gemeinsame Auswahländerungen, Vollprüfung mit Strg+R, sichere Abbruchpunkte und klare Hinweise auf erforderliche Builds.
- Startton: private Mod-Laufzeiten verwenden OpenSmashs vorgesehenen spielbaren EXE-Namen ssbu_user.exe. Gespeicherte Lautstärke wird beim Audio-Start angewendet; keine erzwungenen 100 %, kein F1-Automatismus.
- Native Bereiche Entdecken und Downloads: öffentliche GameBanana-API, SSBU-Suche, Audio, Kategorien, Sortierung, Seiten, Vorschaubilder und sichere Textbeschreibungen.
- Explizite Dateivarianten, persistente Warteschlange mit zwei Streams, Fortschritt, Tempo, Abbruch, Wiederholung, HTTPS-Zielprüfung, Größen-/Hash- und Archivprüfung.
- Gemeinsame Importliste für Downloads und lokale ZIP/RAR; Konflikte pausiert installieren oder vorhandene Partner ausdrücklich pausieren. Duplikate bleiben unverändert.
- Herkunftsmetadaten und Dateiversionen; Updateprüfung zeigt neue Anbieterdateien zur Prüfung an, ohne automatisch zu ersetzen.
- Selbstenthaltender Benutzer-Installer mit Logo-Verknüpfungen; Spiel-/Mod-Assets und lokal erzeugte Spiel-DLLs bleiben außerhalb des Pakets.

# 2.3.3 – Weitergabepaket mit Desktop-Verknüpfung

- Setup erstellt standardmäßig eine Desktop-Verknüpfung mit dem Programmlogo, zusätzlich zum Startmenü-Eintrag. GUI und Kommandozeile nutzen denselben Standard; --no-desktop wählt die Erstellung ab.
- Das Verknüpfungsziel und BrandIcon.ico werden aus dem Installationsordner des Empfängers gebildet. Bestehende eigene Verknüpfungen werden aktualisiert; veraltete feste Spielpfad-Argumente entfallen zugunsten der gespeicherten Einrichtung.
- Enthält sämtliche Korrekturen bis 2.3.2, einschließlich ZIP/RAR, Modpaketen, Dark Mode sowie korrekter Konfigurations-, DLC- und Save-Pfade ohne erzwungene Lautstärke oder Online-Abschaltung.

# 2.3.2 – Bestehende OpenSmash-Einstellungen und DLCs bei Plugin-Starts

- Startet die separate Plugin-EXE mit expliziten Pfaden auf build/config/graphics.ini, controllers.ini und dlc.txt sowie build/saves (auch bei externem Build-Verzeichnis).
- Behebt den falschen relativen Konfigurationsordner verschachtelter Plugin-EXEs: Standardeinstellungen und eine leere DLC-Liste konnten bisher das normale Profil verdecken.
- Entfernt die feste Lautstärke 100 beim normalen Mod-Start; die gespeicherte OpenSmash-Lautstärke gilt wieder.
- Plugin-Buildproben verwenden Kopien aller Konfigurationsdateien. Keine Wiederherstellung alter Saves, kein Überschreiben von Spielkonfiguration oder DLC-Liste.

# 2.3.1 – Direkter RAR-Import

- RAR4/RAR5 und Solid-RARs über Drag & Drop und ZIP/RAR-Mehrfachauswahl, auch in gemischten Stapeln und verschachtelten Sammelarchiven.
- Portable offizielle UnRAR64.dll 7.23.0 mit Prüfsumme, Herkunft und Lizenz enthalten. Kein installiertes WinRAR erforderlich.
- Gemeinsame Archivgrenzen, Pfad-/Linkprüfung, Inhaltsvergleich, CRC-Prüfung und Abbruch. Passwort-/Mehrteilarchive erhalten klare Hinweise.
- UTF-8-Importpläne explizit gelesen, damit Mod-/Ordnernamen mit Umlauten im Rücklesen erhalten bleiben.
- Export bleibt ZIP; bestehende Spielstarts und Mod-Auswahl bleiben erhalten.

# 2.3.0 – Modtypen, Bibliotheksexport und Dark Mode

- Allgemeine Sound-/Ansager-/UI- und Effektpakete, Skyline-NROs samt beliebig benannter lokaler Konfiguration; separate geprüfte Plugin-Übersetzung mit offiziellen Framework-Abhängigkeiten.
- Alle exportieren… sichert alle installierten Mods einschließlich pausierter Einträge und Konfiguration in einer importierbaren ZIP. Keine Spiel-/Save-Dateien oder erzeugten Laufzeiten.
- Inhaltsvergleich überspringt bereits vorhandene Mods in Sammel-ZIPs, mehreren ZIPs und verschachtelten Archiven; neue Einträge behalten den Paketstatus, vorhandene ihren bisherigen Status.
- Gespeicherter heller/dunkler/System-Farbmodus mit passenden Statusfarben, Menüs, Eingaben, Buttons und Windows-Rahmen.
- Gemeinsame Import-/Exportgrenzen 1024 Mods / 64000 Dateien / 8 GiB; Fehler und Abbruch bewahren gültige Profile und bestehende Exportziele.

# 2.2.1 – Neues Emblem und plastische Aqua-Buttons

- Produktname OpenSmash Mod Manager, auch im Startmenü, Fenster und Windows-Deinstallation.
- Transparentes Emblem als Logo, Fenster-/EXE-Icon und Verknüpfungsicon; Windows-ICO mit neun Auflösungen.
- Trebuchet MS als gut lesbare humanistische Schrift mit Aero-Anmutung, Segoe UI als Ausweichschrift; keine Schriftdateien beigelegt.
- Titel und Projektpfad direkt auf dem Glas, ohne weiße Eingabeflächen. Tropfensymbol der Importfläche entfernt.
- Stärkerer Glanz, abgestufte Lichtkanten und sichtbare Button-Sockel; klarer Druckzustand, Kontrastmodus bleibt vereinfacht.
- Bestehende eigene Verknüpfungen werden beim Update sicher umbenannt. Mod-/Spiel- und Profildaten bleiben unverändert.

# 2.2.0 – Milchglas und Stapelimport

- Vier gespeicherte Glaspresets; weniger deckende WPF-Flächen über echtem Desktop Acrylic.
- Mehrfach-ZIP-/Ordnerimport, Bundle-Erkennung, Vorschau je Mod, Konflikt-/Duplikatprüfung, sichere Abbruchpunkte und ein gemeinsamer Undo-Schritt.
- Asynchrone Fortschrittsmeldungen, inkrementelle Bibliothekszeilen, schneller Metadatenstart, weniger redundantes Hashing bei weiterhin vollständiger Mutationsprüfung.
- Benutzerbezogenes Setup, private geprüfte Python-Laufzeit und Bibliotheken, Spielprüfung, Einrichtungsdialog, Verknüpfungen und registrierte Deinstallation.
- Einstellungen und Spiel-/Moddaten bleiben bei Update und Programmdeinstallation erhalten.

# Änderungen

## 2.1.0 – Aqua Glass, 31.10.2026

- Helle, frische Frutiger-Aero-Gestaltung mit Aqua, Sky, Lime, Mint und Eisweiß; auch bei dunklem Windows bleibt die Oberfläche hell.
- Mica ersetzt durch echtes Desktop Acrylic unter Windows 11 ab Build 22621. Durchblick und Blur mit wechselndem nativen Hintergrundmuster visuell bestätigt.
- Dunkle Panel-Verläufe entfernt; polierte Vektorzeichen, kleine Spiegelreflexe, milchige Flächen und klarere Statusfarben ergänzt.
- Hover, Druck, Haken, Auswahl, Tab-/Detailwechsel, Status und Import-Erfolg mit kurzen Übergängen. Fallback für deaktivierte Transparenz, hohe Kontraste, RDP, Energiesparen und eingeschränkte Grafik.
- Suchtext-Clipping korrigiert und kontrastreiche Fokusrahmen ergänzt. Interne Layoutprüfung um 125 Prozent erweitert.
- Mod-Backend, Online-Einstellungen, Installation, Rückbau und Saves bleiben erhalten.
- Dokumentation zu Glas, Fallbacks, Tests und fehlenden C-Entwicklungsheadern aktualisiert.

## 2.0.0 – Milk Glass, 31.10.2026

- Neue WPF-Oberfläche mit ruhiger Typografie, blau-mintfarbenen Lichtakzenten, milchigen Aktionsflächen und gut lesbaren, deckenden Inhaltsbereichen.
- Bibliothek mit Suche, mehrzeiligen Mod-Namen, klarer Auswahl sowie getrennten Details und Aktivitäten. Erfolg, Hinweise und Fehler sind zusätzlich zur Farbe beschriftet.
- Kurze Hover-, Haken- und Detailübergänge; keine dauernden Hintergrundanimationen. Reduzierte Windows-Animationen werden respektiert.
- Helles und dunkles Design nach Windows-Einstellung, Windows-Kontrastfarben und solide Darstellung ohne Glas. Native Mica-Unterstützung auf geeigneten Windows-11-Versionen, sicherer Fallback auf älteren Systemen.
- DPI-Manifest, WPF-Skalierung, Windows-Textvergrößerung, skalierbares Layout und erreichbare Scrollbereiche bei kleinem Fenster. Neue Tastenkürzel und sichtbare Fokuszustände.
- Fehlgeschlagene Vorgänge können über „Erneut versuchen“ wiederholt werden. Python-Ausgaben werden asynchron gelesen; die Oberfläche wartet ohne dauerhaft laufenden Polling-Timer im Leerlauf.
- Die funktionierende Python-Logik für ZIP-/Ordner-Import, Konfigurationen, Aktivierung, Konflikte, Rückgängig und Spielstart bleibt erhalten.
- Der vorherige Online-Fix bleibt enthalten: beide Spielstarts verwenden die gespeicherten OpenSmash-Einstellungen einschließlich Rollback.
- Paket enthält XAML, DPI-Manifest, aktualisierten EXE-Host samt Quellcode, diese Versionshinweise, Design-Dokumentation und überarbeitete Anleitung.
