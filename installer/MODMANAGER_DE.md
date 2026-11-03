# Modmanager 3.7.0: Bedienung und Ladeverfahren

Strg+O öffnet die ZIP-/RAR-/7z-Mehrfachauswahl, Strg+Umschalt+O den Ordnerdialog, Strg+I installiert die geprüfte Vorschau. Strg+F sucht, Strg+L öffnet Protokolle, Strg+Z nimmt den letzten Stapel zurück. F5 startet mit Mods, F6 Vanilla. Haken aktivieren oder pausieren; Änderungen gelten beim nächsten Spielstart.

Der Import prüft Archiv-Pfade, Größe, Konfiguration und SHA-256. Wrapper wie ultimate/mods werden aufgelöst; getrennte Modordner und verschachtelte ZIP-/RAR-/7z-Dateien werden allgemein erkannt. Der Inhaltsvergleich berücksichtigt wirksame Dateien und Plugin-Konfiguration, unabhängig von Archivname und info.toml-Beschriftung. Vorhandene Inhalte bleiben mit ihrer bisherigen Aktivierung erhalten. Namensgleiche neue Inhalte erhalten einen Zusatz; Dateikonflikte zwischen aktiven Mods werden erklärt. Neue pausierte Paketmods können ohne Aktivierung übernommen werden.

ARCropolis-Assets behalten Kostümpfade, Unsharing, zusätzliche Dateien, regionale Dateien, XML-/XMSBT-/PRCXML-Merges und config.json. Mod-lokale NROs werden validiert und mit OpenSmash übersetzt. Zusätzliche TOML-/JSON-/INI-Konfiguration bleibt im Modordner erhalten. Externe Windows-DLLs, EXEs und Skripte werden abgelehnt.

Die getrennte Plugin-Laufzeit liegt in build/work/modmanager_plugins unter einem Inhalts-/ABI-Schlüssel. Offizielle Smashline- und nro-hook-Abhängigkeiten werden bei Bedarf mit festen Prüfsummen geladen. Hook-Stellen werden mit kopierten Saves und Testkonfiguration aufgezeichnet; main und common werden aus vorhandenen lokalen Quellen neu übersetzt. Die ursprüngliche Spiel-EXE und die Basis-ARC-Laufzeit bleiben erhalten. Erst nach Probe mit gemountetem Moddateisystem und aktiven benötigten Hooks wird der Cache freigegeben. Zwei dokumentierte Smashline-SDK-Unwind-Hooks übernimmt OpenSmash selbst über nnunwind; weitere inaktive Hooks oder Laufzeitfehler lehnen den Build ab.

Ein Import bereitet eigene Kopien und ein neues Profil vor. Der Profilwechsel erfolgt erst nach erfolgreicher Prüfung und einem letzten Abbruchpunkt. Ein nicht übersetzbares neues Plugin kann abgelehnt werden, während gültige reine Asset-Mods desselben Stapels installiert werden. Ein Undo gilt für den gesamten erfolgreichen Stapel. Spiel und andere Manager müssen während Änderungen geschlossen sein.

**Mehr > Alle Mods als ZIP exportieren…** erstellt atomar eine geprüfte ZIP mit allen Bibliotheksmods einschließlich pausierter Einträge. opensmash-pack.json enthält relative Pfade, Prüfsummen und Aktivierung. Spiel-/Save-Dateien, absolute Pfade, Abhängigkeitendownloads und erzeugte Laufzeiten werden nicht exportiert. Empfänger ziehen das Paket wie eine normale ZIP hinein. Grenzen: 1024 Mods, 64000 Archiveinträge, 8 GiB entpackt; Manifest höchstens 16 MiB.

**Design** speichert Light/Dark/System. Alle Flächen sind deckend, Desktop Acrylic und Glasoptionen sind entfernt. Alte Glaswerte werden beim Öffnen auf Solid migriert. Windows-Kontrastfarben haben Vorrang. Export, Gruppenaktionen, Vollprüfung, Updateprüfung und Protokolle liegen unter **Mehr**.

Normale Spielstarts übernehmen bestehende Online-/Rollback-Einstellungen. Nur Build- und Laufzeitproben verwenden Offline-Prozesse und kopierte Saves. Protokolle liegen in opensmash_mods/logs. Nach OpenSmash-Änderungen kann ein neuer lokaler Build notwendig werden. Update/Programmdeinstallation bewahren Spiel, Modbibliothek und Benutzereinstellungen.


Der RAR-Import nutzt die beigelegte offizielle UnRAR64.dll 7.23.0 mit fester SHA-256. Beide Formate verwenden dieselben Pfad-/Duplikat-/Budgetregeln. Vor der Dekompression werden alle RAR-Einträge geprüft; die DLL liefert nur Datenblöcke im Testmodus. Ausschließlich der Manager schreibt in eigene Importordner. CRC-/BLAKE2-Prüfung, Größenvergleich und sichere Abbruchpunkte bleiben aktiv, auch bei Solid-Archiven. Verknüpfungen werden abgelehnt; von der DLL normalisierte Namen werden ebenfalls vor dem Schreiben validiert. Keine DLL-gesteuerte Pfadextraktion und keine System-WinRAR-Abhängigkeit. Eigene UTF-8-Importpläne werden explizit als UTF-8 gelesen, damit Umlaute erhalten bleiben.


NEU IN 3.2: CHARAKTERE, VOLLBILD UND GAMEBANANA-LINKS
In Entdecken unter Charakter z.B. Sora auswaehlen. Das zeigt die echten
Skin-Unterkategorien von GameBanana, einschliesslich deren Sortierung und
Seiten. Bei Auswahl eines Charakters wechselt die Kategorie zu Skins.
Der Filter gilt fuer Skins; Audio hat keine entsprechende Charakterstruktur.
Fuer eine freie Textsuche zuerst Alle Charaktere waehlen. Die GameBanana-
Textsuche bietet keinen zuverlaessigen kombinierten Charakterfilter.

Auf das grosse Vorschaubild in den Moddetails klicken: Vollbildansicht mit
dem groesseren Anbieterbild. Pfeile links/rechts wechseln Bilder, Esc oder
Schliessen beendet die Ansicht. Sehr grosse Bilder werden auf maximal
4096 x 4096 Pixel begrenzt; die Quelle bestimmt die verfuegbare Aufloesung.

Mehr > GameBanana-Link oeffnen... akzeptiert eine normale Mod-/Soundseite
oder einen kopierten 1-Click-Link. Eine Seite oeffnet erst die Dateiauswahl.
Ein vollstaendiger Dateilink startet den Download der verlinkten Variante;
nach dem Download immer Auswahl pruefen & installieren benutzen.
Eine unterstuetzte ZIP-/RAR-/7z-Variante in den Moddetails auswaehlen und
Mehr > Manager-Link zur Datei kopieren erzeugt einen opensmashmm:-Link.
Setup registriert dieses Protokoll fuer dein Windows-Benutzerkonto.
Der Link oeffnet den Manager bzw. wird an den laufenden Manager uebergeben.
Ein funktionierender Spielordner muss zuvor verbunden sein. Browser koennen
vor dem Oeffnen einer externen Anwendung einmal nachfragen.

Der vorhandene MOSAIC-/FightPlanner-Button auf GameBanana gehoert zu diesem
anderen Programm und wird nicht umgebogen. Kopierte fightplanner:-Links
koennen ausdruecklich im Linkdialog eingefuegt werden. Ein eigener OpenSmash-
Button direkt auf GameBanana erfordert zusaetzlich deren Website-Integration;
die lokale Installation allein fuegt dort keinen Button hinzu.
Nur oeffentliche SSBU-Dateien werden ueber die Anbieter-API aufgeloest.
Links installieren oder aktivieren keine Mods automatisch.

## Bibliotheksansicht, Titelbilder und Downloads

**Liste / Kacheln** verwendet dieselbe Auswahl, Suche und Aktivierung. Ein Titelbild bleibt reine Darstellung außerhalb der spielbaren Moddateien. Optional: preview/thumbnail/cover als PNG, JPG oder WebP im Modordner. **Mehr > Titelbild auswählen…** akzeptiert ein eigenes Bild bis 8 MiB und 20 Millionen Pixel; gespeichert wird eine verkleinerte PNG-Vorschau. Für GameBanana-Imports wird ausschließlich die gespeicherte Herkunft verwendet. Alte Imports ohne Herkunft erhalten keine erratenen Bilder.

**Downloads > Download entfernen** löscht ausgewählte abgeschlossene, fehlgeschlagene oder abgebrochene Einträge und deren zwischengespeicherte Archive. Laufende Downloads zuerst abbrechen. Installierte Mods und bereits vorbereitete Importkopien werden dadurch nicht entfernt.

Die Gameplay-Prüfung kennt Param Config, CSK und One Slot Effects anhand von Bibliotheksverweisen bzw. zusätzlichen Effekt-Slots, unabhängig vom Modnamen. Bekannte Spielversionskonflikte werden vor dem Build erklärt. Die öffentlich angebotene CSK 5.0.6 ist für 13.0.4; für das unterstützte 13.0.5 wird CSK 6.0.0 benötigt. Shadow bleibt bis zu einer passenden, erfolgreich lokal geprüften Bibliothek unbestätigt. Native fighter.json-/Windows-DLL-Pakete sind weiterhin nicht importierbar. Details und offener Testbefund: BEKANNTE_EINSCHRAENKUNGEN.md.


Neu in 3.5: Modlisten ohne Moddateien teilen

Mehr > Modliste teilen… speichert eine kleine .opensmash-list.json. Empfänger
öffnen Mehr > Modliste importieren… oder ziehen die Datei auf die Bibliothek.
Nach der Vorschau lädt „Fehlende Mods installieren“ die fehlenden Originaldateien
herunter und installiert nur die angeforderten Inhalte. Bereits vorhandene Mods
behalten ihre Aktivierung; Dateikonflikte werden pausiert installiert. Lokale Mods
ohne gespeicherte Anbieterquelle sowie unveröffentlichte eigene Änderungen
benötigen weiterhin Originaldateien oder den bisherigen ZIP-Export. Entfernte
oder veränderte Anbieterdateien werden gemeldet, keine andere Version eingesetzt.

„Dateien für Auswahl…“ heißt jetzt „Ausgewählte Mods herunterladen…“ und erscheint
nur bei Mehrfachauswahl. Die Downloadliste bleibt beim Aktualisieren ruhig.
Der gemeldete CSK-Versionskonflikt wird vor der Übersetzung erkannt; unabhängige
Asset-Imports erzwingen keinen Neuaufbau derselben Plugin-Laufzeit. Näheres:
BEKANNTE_EINSCHRAENKUNGEN.md. Shadow ist weiterhin nicht als spielbar bestätigt.


Neu in 3.6: 7z-Dateien lassen sich wie ZIP und RAR direkt importieren und
über GameBanana herunterladen. „Manuell“ wegen einer 7z-Endung entfällt.
Andere öffentliche Dateiformate lassen sich als „Nur Download“ laden und mit
„Datei speichern…“ ablegen; sie werden nicht automatisch installiert.
„Alle Downloads löschen…“ entfernt nach Bestätigung Einträge und Archive und
bricht laufende Transfers ab. Installierte Mods bleiben erhalten. Neue Moddetails
unter Entdecken beginnen ganz oben. Die passende CSK-Version 6.0.0 für 13.0.5
war bei erneuter Prüfung nicht öffentlich verfügbar; die inkompatible 5.0.6
wird weiterhin blockiert. Einzelheiten: BEKANNTE_EINSCHRAENKUNGEN.md.
