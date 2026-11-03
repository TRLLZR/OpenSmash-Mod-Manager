# Design-Review und Darstellung 3.3

Gesamturteil nach apple-design: **Gut**. Zweck ist, Mods auszuwählen und schnell zu spielen. Das bereitgestellte Aero-Wortlogo und passende plastische Buttons prägen die Anwendung. Die gemeinsame Vorlage ersetzt abweichende flache QuietButtons: 42 DIP Mindesthöhe, Radius 14, Tiefenkante 3 DIP, Hover-/Druckzustand und sichtbarer Tastaturfokus. Grün kennzeichnet Start/Installation/Download. Normale Aktionen verwenden einen blauweißen beziehungsweise dunkelblauen Verlauf. Die Aufhellung endet oberhalb der Beschriftung. Kontrastdarstellung verzichtet auf Dekoration.

Verbesserungen: selten benötigte Pfade als Detail-Tooltip, Installationshinweise aufklappbar, Entfernen und Rückgängig kontextabhängig. Die unvollständige Übersetzung älterer Diagnosen bleibt eine Einschränkung. Das ist ein Windows/WPF-Produkt; macOS-Menükonventionen wurden nicht übernommen.

Gemessene Tokenkontraste: heller Button #0D323C auf #B8E3EC 9,90:1; grüner heller Button #204B32 auf #A9DA69 6,11:1; dunkler normaler Button #E9F6FA auf #3E6173 6,02:1; sekundärer Text hell 11,83:1 und dunkel 8,72:1. Tokenmessungen ersetzen keine vollständige pixelweise Kontrastprüfung. Haupttext 14 DIP, Metatext mindestens 13 DIP; Windows-Textskalierung bleibt unterstützt.

Verwendete Prinzipien: `buttons.md › Best practices`: „Always include a press state for a custom button.“ `layout.md › Visual hierarchy`: „Use progressive disclosure to make layouts cleaner and easier to interact with.“ `settings.md › Best practices`: „Minimize the number of settings you offer.“ `accessibility.md › Vision`: „Support larger text sizes.“ Platzierung und Farbverläufe sind Produkturteil anhand des Benutzerbildes.

Reguläre Struktur:
```
Logo                              Design | Mehr
Mods hinzufügen                   Dateien | Ordner
Bibliothek | Entdecken | Downloads
Bibliothek + Suche                Details / Importliste
Status                            Mit Mods | Vanilla
```
Bei kompakter Breite bleiben dieselben Funktionen und Tastaturaktionen erhalten; Filter umbrechen, die äußere Scrollfläche fängt große Textskalierung ab. Es gibt keine zusätzliche Einführungsanimation. Reduzierte Bewegung schaltet kurze Zustandsübergänge aus. Die Tests umfassen 60 Layoutfälle und zusätzliche native Sprachvorschauen einschließlich RTL.

## Erhaltene Grundlagen aus 3.1

# Layout und Darstellung 3.1

Die Oberfläche priorisiert die Modbibliothek und den nächsten Arbeitsschritt. Das bereitgestellte Wort-/Bildlogo steht einmal oben links; ein separater Produkttitel im Inhalt entfällt. Der normale Windows-Fenstertitel bleibt für Taskleiste und Barrierefreiheit erhalten.

Drei eindeutige Hauptbereiche: Bibliothek, Entdecken, Downloads. Aktive Navigation hat eine benannte Auswahl und eigene Fläche. Häufige Aktionen sind sichtbar; seltenere Aktionen bleiben im Mehr-Menü und über bisherige Tastenkürzel erreichbar. Die Dateiauswahl und Drag-&-Drop-Fläche bilden eine kurze Importleiste. Installieren erscheint mit prüfbarer Vorschau; Konfliktaktionen hängen vom ausgewählten Eintrag ab.

Alle Hintergrund-, Panel-, Menü- und Zeilenflächen sind deckend. Der native Desktop-Backdrop bleibt ausgeschaltet. Lokale Buttons behalten ihre Aero-Farbverläufe und Tiefe, die Seiten selbst haben keinen Glaseffekt. Hell/Dunkel/System und die Windows-Kontrastfarben bleiben erhalten. Alte Glaspräferenzen werden als Solid gelesen und beim Öffnen gespeichert.

Trebuchet MS / Segoe UI, System-Textskalierung, Tastaturfokus und benannte Controls bleiben erhalten. Listen sind weiterhin virtualisiert. Lange Texte und Pfade laufen über Tooltip, Details oder Protokolle statt über die Hauptnavigation. Fehler und echte Konflikte bleiben sichtbar.

Prüfhilfe: Apple-Design-Skill, für Windows/WPF übersetzte Prinzipien aus layout.md › Visual hierarchy, branding.md › Best practices, writing.md › Best practices, accessibility.md › Vision und toolbars.md › Best practices. Dies ist keine Übernahme macOS-spezifischer Navigation. Die Entscheidung für vollständig deckende Flächen folgt ausdrücklich dem Benutzerwunsch.

## Bibliothek 3.4

Liste und Kacheln teilen Auswahl, Suche und Aktivierung. Ein ruhiges Vorschaubild ergänzt den Modtitel; unbekannte Quellen behalten einen neutralen Platzhalter. Zwei direkte Ansichtsbuttons zeigen die gespeicherte Wahl. Gleiche Kachelhöhen halten die Aktivierungsschalter ausgerichtet. Die vorhandene Aero-Buttonvorlage bleibt maßgeblich.

Verwendete zusätzliche apple-design-Referenzen: `collections.md > Best practices`: „Use the standard row or grid layout whenever possible.“ und `lists-and-tables.md > Best practices`: „Provide appropriate feedback when people select a list item.“ Das Raster, die Bildgrößen und die gemeinsame Datenauswahl sind die konkrete Übertragung auf WPF.

## Rückmeldung und Auswahl 3.5

Downloadzeilen behalten Identität, Tastaturfokus und Auswahl. Polling startet
keine Auswahlbewegung. Stapelaktionen erscheinen nur bei Mehrfachauswahl.
Die Modliste verwendet dieselbe Vorschau mit klarer Bestätigung. Zusätzliche
apple-design-Referenzen: `motion.md > Best practices`: „Add motion purposefully,
supporting the experience without overshadowing it.“ und `feedback.md > Best
practices`: „Consider integrating status feedback into your interface.“ Die WPF-
Datenbindung ist Implementierungsentscheidung, keine Apple-Plattformkonformität.


## Download-Aktionen 3.6: gezielte Designprüfung

Bewertung: Gut. Die Downloadansicht dient dem Prüfen, Installieren und Aufräumen;
die vorhandenen plastischen Buttons und die OpenSmash-Wortmarke bleiben erhalten.
Die primäre Installation verwendet dieselbe Buttonvorlage wie die Startaktionen.
Die Löschaktion ist ausdrücklich beschriftet und verlangt eine kurze Bestätigung
mit Abbrechen/Esc. Es gibt keine zusätzliche Erfolgsmeldung als Dialog.

„Datei speichern…“ erscheint nur für eine ausgewählte Datei ohne direkten
Importweg. Das spart eine dauerhafte Zusatzoption. Der Bestätigungsdialog wächst
mit seinem Text statt eine feste Höhe vorzugeben. Die Aktionsleiste bricht bei
kleiner Breite um. Der Modwechsel setzt die Beschreibung gezielt an den Anfang;
die regelmäßige Downloadaktualisierung verändert weder Fokus noch Auswahl.

Übertragene Grundsätze des apple-design-Skills: buttons.md > Content:
„Ensure that each button clearly communicates its purpose.“ alerts.md > Best
practices: „Use alerts sparingly.“ layout.md > Adaptability:
„Be prepared for text-size changes.“ Dies sind allgemeine Bediengrundsätze;
die Implementierung bleibt eine native Windows-WPF-Anwendung. Licht-/Dunkel-,
Kontrastfarben, Schrift- und Fokusregeln verwenden die bestehenden Designtokens.
