# OpenSmash Mod Manager 3.7.0

Native Windows-Modbibliothek für ein vorhandenes OpenSmash-Spiel. ZIP vollständig entpacken, **Setup.exe** starten und den eingerichteten OpenSmash-Ordner auswählen. Die Installation gilt für dein Benutzerkonto. Spiel, Nintendo-Dateien und fremde Mods sind nicht enthalten.

## Mods verwenden

1. ZIP-/RAR-/7z-Dateien oder Mod-Ordner auf **Mods hinzufügen** ziehen.
2. Importliste prüfen, Konflikte entscheiden und **Installieren** wählen.
3. Haken in der Bibliothek schalten Mods aktiv oder pausiert. Änderungen gelten beim nächsten Spielstart. **Rückgängig** stellt die vorherige Auswahl wieder her.
4. **Mit Mods spielen** oder **Vanilla spielen** starten.

Unter **Entdecken** findest du öffentliche GameBanana-Mods. Eine Dateivariante auswählen und herunterladen. In **Downloads** die Auswahl prüfen und die Installation gesondert bestätigen. Downloads und Manager-Links installieren niemals automatisch. Bilder öffnen sich per Klick im Vollbild; Pfeiltasten und Esc stehen zur Verfügung. Charakterfilter verwenden echte Skin-Unterkategorien. Die getrennte Textsuche folgt den Einschränkungen der GameBanana-Such-API.

**Mehr** enthält Export als ZIP, Gruppenaktionen, vollständige Bibliotheksprüfung, Updates, Protokolle und Manager-Links. Der eigene `opensmashmm:`-Handler verändert MOSAIC/FightPlanner nicht. Ein eigener Website-Button auf GameBanana ist noch nicht veröffentlicht.

## Darstellung und Sprache

Einheitliche runde Buttons mit leichter Tiefenkante entsprechen dem bereitgestellten Vorbild. **Design** bietet Hell, Dunkel und **Wie Windows**. Alle Flächen bleiben deckend. Windows-Kontrastfarben und reduzierte Animationen haben Vorrang. Bestehende Einstellungen bleiben erhalten; neue Installationen folgen Windows.

Die Windows-Anzeigesprache wird automatisch übernommen. Kernabläufe sind in 16 Sprachfamilien verfügbar. Ergänzende Erklärungen verwenden teils Englisch als Rückfall; ältere technische Backendmeldungen sind teils noch Deutsch. Fremde Modbeschreibungen, Dateinamen und Charakternamen bleiben im Original. Es gibt keine Online-Übersetzung in der Anwendung. Einzelheiten zur Abdeckung: **BEKANNTE_EINSCHRAENKUNGEN.md**, ergänzende englische Architektur-/Build-Dokumentation: **README.md**.

## Unterstützung und Grenzen

Modtypen werden anhand ihrer Struktur erkannt. Assets, Skins, Sounds, UI, ARC-Konfiguration und unterstützte Skyline-NRO-Plugins verwenden die vorhandenen OpenSmash-Ladeverfahren. Erste Builds können mehrere Minuten dauern und Clang, C++ Build Tools sowie das Windows SDK benötigen. Eine passende Dateistruktur garantiert nicht, dass ein fremder Mod im Spiel funktioniert. Windows-Programme und Installationsskripte werden nicht importiert.

Grenzen pro Stapel: 1024 Mods, 64000 Einträge, 8 GiB entpackt. Doppelte Inhalte werden ausgelassen; bestehende Aktivierungen bleiben erhalten. Der ZIP-Export enthält auch pausierte Mods und deren Auswahl. Weitergabe fremder Mod-Assets erfordert die entsprechenden Rechte der Autoren.

Spielkonfiguration, Saves, DLC-, Online- und Lautstärkeeinstellungen bleiben außerhalb des Manager-Updates. **ANLEITUNG.txt** und **MODMANAGER_DE.md** erklären die Bedienung ausführlicher. **SECURITY.md** beschreibt Sicherheitsprüfung und Grenzen; **THIRD_PARTY_NOTICES.txt** enthält Lizenzhinweise.

## Bibliothek und Darstellung

**Liste / Kacheln** schaltet die Bibliotheksansicht um und merkt sich deine Wahl. Titelbilder werden aus lokalen Vorschauen oder gespeicherter GameBanana-Herkunft geladen. **Mehr > Titelbild auswählen…** setzt ein eigenes Bild. Ohne passende Quelle bleibt ein neutraler Platzhalter.

In **Downloads** entfernt **Download entfernen** fertige, fehlgeschlagene oder abgebrochene Downloads einschließlich des gespeicherten Archivs. Installierte Mods bleiben erhalten.

Gameplay-Mods werden anhand von NRO-Verweisen und zusätzlichen Kostüm-/Effektdateien geprüft. Bei Shadow fehlt derzeit eine öffentlich verfügbare passende CSK-Bibliothek für 13.0.5; die alte 5.0.6 wird wegen Versionskonflikt blockiert. Shadow ist deshalb noch nicht als spielbar bestätigt. Siehe BEKANNTE_EINSCHRAENKUNGEN.md.


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


## Veröffentlichung und neue Logos in 3.7

Wortmarke und Windows-Symbol verwenden die getrennten transparenten Bestandteile
der neuen bereitgestellten ChatGPT-Grafik. Herkunft und Grenzen stehen in
BRANDING.md. Die vorhandenen Lizenzen und Copyright-Hinweise der Bibliotheken
bleiben erhalten. LEGAL_REVIEW.md dokumentiert die technische Prüfung; dies ist
keine rechtliche Freigabe. Das eigene GitHub-Quellpaket enthält keine Spieldaten,
privaten Protokolle oder Testdownloads. README.md erklärt die Entwicklung auf
Englisch; die GitHub-Startseite enthält die englische Übersicht für Anwender.
