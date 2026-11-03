# Bekannte Grenzen in 3.7.0

- Allgemeine ARCropolis-Skins, Sound/UI/Effekt-Assets und übersetzbare Skyline-NROs sind unterstützt. Es gibt keine Garantie für jedes beliebige Gameplay-Plugin: OpenSmashs vorhandener Lifter, verfügbare Hooks und unterstützte Instruktionen bestimmen die Kompatibilität. Fehlgeschlagene Plugin-Builds werden erklärt und ersetzen kein gültiges Profil.
- Automatisch aufgelöste Framework-Versionen sind Smashline 2.0.0 und nro-hook 0.4.0. Mods mit anderen zwingenden Framework-Versionen oder weiteren nicht mitgelieferten Abhängigkeiten können zusätzliche Anpassungen benötigen.
- Unterschiedliche aktive Dateien am selben Ziel sind ein Konflikt. Zwei Ansager-/UI-Pakete können dieselben Dateien ersetzen; einzeln funktionieren sie, gemeinsam müssen sie pausiert/ausgetauscht werden. Gleicher Inhalt wird hingegen übersprungen.
- Ein Auftrag bzw. Exportpaket umfasst höchstens 1024 Mods, 64000 Archiveinträge und 8 GiB entpackt. ZIP/RAR/7z ineinander bis zwei Archivebenen; Manifest höchstens 16 MiB. RAR4/RAR5 und 7z einschließlich Solid werden direkt unterstützt. Verschlüsselte und mehrteilige Archive vorher entpacken. RAR-Wörterbuch höchstens 512 MiB; 7z-Decoder höchstens 768 MiB Arbeitsspeicher. Keine Windows-Programme oder Installationsskripte als Mod.
- Eigene vollständige OpenSmash-13.0.5-Builddaten, Clang, C++ Build Tools und Windows SDK sind für die lokale Mod-Laufzeit erforderlich. Ein reines vorgefertigtes Spielpaket reicht gegebenenfalls nicht aus. Erste Builds brauchen Internet, Platz und mehrere Minuten.
- Online-Teilnehmer benötigen passende Spiel-/Modversionen. Erfolgreicher lokaler Start bestätigt keine allgemeine Online-Synchronität beliebiger Gameplay-Mods.
- Die Oberfläche ist vollständig deckend; es gibt keinen zuschaltbaren Hintergrundglas-Modus. Hell/Dunkel/System sowie Windows-Kontrastfarben bleiben vorhanden. Wie Windows wird beim Öffnen/Auswählen ausgewertet, nicht laufend überwacht.
- Die ältere native Dry-Bowser-Teillösung behält ihre bisherigen Grenzen; Standard-ARCropolis-Import verwendet die vollständige Modquelle. Keine zweite physische Kollegeninstallation und kein realer Windows-10-/RDP-Test wurden behauptet.


## GameBanana und Validierung

- Öffentliche API v11 ohne Anmeldung; 1 API-Anfrage pro Sekunde als eigene konservative Begrenzung, Cache und Beachtung von HTTP 429/Retry-After. Dies ist keine zugesagte Anbieterquote. Änderungen/Netzwerkausfälle können manuelles Herunterladen erfordern.
- Textsuche ist API-Relevanzsuche innerhalb der gewählten Art Mod/Sound. Kategorien und Sortierung gelten für den Katalog ohne Suchtext. Downloadzahlen erscheinen nur, wenn der Anbieter sie liefert.
- Direkte öffentliche Dateien bis 2 GiB; maximal zwei Streams. Entpackgrenzen bleiben 8 GiB/64000 Einträge pro Prüfung/Stapel. ZIP/RAR/7z können direkt importiert werden. Andere Formate sind „Nur Download“ und müssen nach „Datei speichern…“ manuell verarbeitet werden. Zugriffsbeschränkungen werden nicht umgangen.
- Beschreibung als reiner Text, keine ausgeführten Skripte. Nicht strukturierte Abhängigkeiten lassen sich nicht zuverlässig automatisch auflösen: Beschreibung und beigefügte Anleitung bleiben maßgeblich.
- Erfolgreiche Importprüfung ergibt Experimental, keine pauschale Spielgarantie. Der Live-Download wurde in einer isolierten Testbibliothek installiert und nicht als im Spiel verifiziert ausgegeben.
- Updateprüfung erkennt neue Dateivarianten oder geänderte Anbieter-Hashes. Sie wählt keine Variante automatisch und überschreibt keine geänderten lokalen Assets. Zurückstufen auf ältere Manager nach neuen Transaktionen ist nicht unterstützt.
- Erstvalidierung, neue große Dateien, Export und vollständige Prüfung benötigen weiterhin echte Datei-I/O. Neue/geänderte NRO-Sätze oder ihre Plugin-Konfiguration können minutenlange lokale Builds benötigen. Abbruch wartet auf sichere Prüfpunkte.
- Tatsächlicher Startton wurde mit Mods, Vanilla, Neustarts, gespeichertem 70/37-%-Pegel und erneut geöffnetem Manager mittels Windows-Audioausgabe-Diagnostik bestätigt. Manueller F1-Reglertest blieb wegen abgelaufener Fensterfreigabe ungeprüft; Rechnerneustart wurde in der interaktiven Sitzung nicht durchgeführt. Der vorhandene F1-Code wurde nicht geändert.

- Der Charakterfilter bildet die Skin-Unterkategorien von GameBanana ab. Audio und andere Kategorien haben dort keine entsprechende Struktur. Textsuche und Charakterkatalog sind getrennt, da die Such-API den Kategorieparameter ignoriert. Vollbildbilder verwenden die verfuegbare Anbieteraufloesung bis 4096 x 4096 Pixel.
- opensmashmm: ist der eigene lokale Dateilink. Der MOSAIC-Button gehoert zu einem anderen Manager. Ein eigener GameBanana-Button setzt eine zusaetzliche Website-Integration voraus; diese Version veroeffentlicht keine solche Integration. Browser koennen fuer externe Programme eine Rueckfrage anzeigen. Ein bereits mit einem anderen Programm belegtes opensmashmm:-Protokoll wird vom Setup erklaert abgelehnt.

## Gameplay-Befund 3.4

Shadow verlangt Param Config und CSK; seine zusätzlichen Kostüme werden erkannt. Der isolierte 13.0.5-Lauf mit der öffentlich angebotenen CSK 5.0.6 brach vor dem Spielstart ab. Diese 13.0.4-Bibliothek wird nicht automatisch für 13.0.5 eingesetzt. Eine passende CSK 6.0.0 war auf der offiziellen Downloadseite nicht verfügbar. Shadow ist noch nicht spielbar bestätigt. Das Update verändert die bestehende Modauswahl nicht. Auch andere Mods mit dieser fehlenden Abhängigkeit bleiben blockiert. Native fighter.json-Pakete mit Windows-DLLs bleiben außerhalb der unterstützten Importformate.
