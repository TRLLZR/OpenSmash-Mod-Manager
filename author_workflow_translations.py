"""Reviewed translations of the primary workflow. No runtime translation service."""

import json
from pathlib import Path

LANGUAGES = "es fr it pt nl pl tr ru uk ja ko zh-CN zh-TW ar".split()
# Columns follow LANGUAGES; preserve access keys and formatting placeholders.
ROWS = """
Modliste teilen…|Compartir lista de mods…|Partager la liste de mods…|Condividi elenco mod…|Compartilhar lista de mods…|Modlijst delen…|Udostępnij listę modów…|Mod listesini paylaş…|Поделиться списком модов…|Поділитися списком модів…|MODリストを共有…|모드 목록 공유…|分享模组列表…|分享模組清單…|مشاركة قائمة التعديلات…
Modliste importieren…|Importar lista de mods…|Importer une liste de mods…|Importa elenco mod…|Importar lista de mods…|Modlijst importeren…|Importuj listę modów…|Mod listesini içe aktar…|Импорт списка модов…|Імпортувати список модів…|MODリストを読み込む…|모드 목록 가져오기…|导入模组列表…|匯入模組清單…|استيراد قائمة التعديلات…
Modliste gespeichert|Lista de mods guardada|Liste de mods enregistrée|Elenco mod salvato|Lista de mods salva|Modlijst opgeslagen|Lista modów zapisana|Mod listesi kaydedildi|Список модов сохранён|Список модів збережено|MODリストを保存しました|모드 목록 저장됨|模组列表已保存|模組清單已儲存|تم حفظ قائمة التعديلات
Fehlende Mods installieren|Instalar mods que faltan|Installer les mods manquants|Installa mod mancanti|Instalar mods ausentes|Ontbrekende mods installeren|Zainstaluj brakujące mody|Eksik modları yükle|Установить недостающие моды|Встановити відсутні моди|不足しているMODをインストール|누락된 모드 설치|安装缺少的模组|安裝缺少的模組|تثبيت التعديلات الناقصة
Ausgewählte Mods herunterladen…|Descargar mods seleccionados…|Télécharger les mods sélectionnés…|Scarica mod selezionate…|Baixar mods selecionados…|Geselecteerde mods downloaden…|Pobierz wybrane mody…|Seçili modları indir…|Скачать выбранные моды…|Завантажити вибрані моди…|選択したMODをダウンロード…|선택한 모드 다운로드…|下载选中的模组…|下載所選模組…|تنزيل التعديلات المحددة…
Liste|Lista|Liste|Elenco|Lista|Lijst|Lista|Liste|Список|Список|リスト|목록|列表|清單|قائمة
Kacheln|Mosaico|Vignettes|Riquadri|Blocos|Tegels|Kafelki|Kutucuklar|Плитки|Плитки|タイル|타일|平铺|磚塊|بطاقات
Listenansicht|Vista de lista|Vue en liste|Vista elenco|Exibição em lista|Lijstweergave|Widok listy|Liste görünümü|Вид списком|Вигляд списком|リスト表示|목록 보기|列表视图|清單檢視|عرض القائمة
Kachelansicht|Vista de mosaico|Vue en vignettes|Vista riquadri|Exibição em blocos|Tegelweergave|Widok kafelków|Kutucuk görünümü|Вид плитками|Вигляд плитками|タイル表示|타일 보기|平铺视图|磚塊檢視|عرض البطاقات
Download entfernen|Eliminar descarga|Supprimer le téléchargement|Rimuovi download|Remover download|Download verwijderen|Usuń pobranie|İndirmeyi kaldır|Удалить загрузку|Видалити завантаження|ダウンロードを削除|다운로드 제거|移除下载|移除下載|إزالة التنزيل
Titelbild auswählen|Elegir portada|Choisir une image|Scegli copertina|Escolher capa|Omslag kiezen|Wybierz okładkę|Kapak resmi seç|Выбрать обложку|Вибрати обкладинку|カバーを選択|표지 선택|选择封面|選擇封面|اختيار صورة الغلاف
Ausgewählt|Seleccionado|Sélectionné|Selezionato|Selecionado|Geselecteerd|Wybrano|Seçili|Выбрано|Вибрано|選択済み|선택됨|已选择|已選取|محدد
Bibliothek|Biblioteca|Bibliothèque|Libreria|Biblioteca|Bibliotheek|Biblioteka|Kütüphane|Библиотека|Бібліотека|ライブラリ|라이브러리|模组库|模組庫|المكتبة
Entdecken|Descubrir|Découvrir|Scopri|Descobrir|Ontdekken|Odkrywaj|Keşfet|Обзор|Огляд|見つける|탐색|发现|探索|استكشاف
Downloads|Descargas|Téléchargements|Download|Downloads|Downloads|Pobieranie|İndirilenler|Загрузки|Завантаження|ダウンロード|다운로드|下载|下載|التنزيلات
Design|Apariencia|Apparence|Aspetto|Aparência|Weergave|Wygląd|Görünüm|Оформление|Вигляд|外観|화면 설정|外观|外觀|المظهر
Mehr ⋯|Más ⋯|Plus ⋯|Altro ⋯|Mais ⋯|Meer ⋯|Więcej ⋯|Diğer ⋯|Ещё ⋯|Ще ⋯|その他 ⋯|더 보기 ⋯|更多 ⋯|更多 ⋯|المزيد ⋯
Dateien…|Archivos…|Fichiers…|File…|Arquivos…|Bestanden…|Pliki…|Dosyalar…|Файлы…|Файли…|ファイル…|파일…|文件…|檔案…|ملفات…
Ordner…|Carpeta…|Dossier…|Cartella…|Pasta…|Map…|Folder…|Klasör…|Папка…|Папка…|フォルダー…|폴더…|文件夹…|資料夾…|مجلد…
Installieren|Instalar|Installer|Installa|Instalar|Installeren|Zainstaluj|Yükle|Установить|Установити|インストール|설치|安装|安裝|تثبيت
Mods hinzufügen|Añadir mods|Ajouter des mods|Aggiungi mod|Adicionar mods|Mods toevoegen|Dodaj mody|Mod ekle|Добавить моды|Додати моди|MODを追加|모드 추가|添加模组|新增模組|إضافة تعديلات
ZIP/RAR/7z oder Ordner hier ablegen|Arrastra archivos ZIP/RAR/7z o carpetas aquí|Déposez des fichiers ZIP/RAR/7z ou dossiers ici|Trascina qui file ZIP/RAR/7z o cartelle|Solte arquivos ZIP/RAR/7z ou pastas aqui|Sleep ZIP/RAR/7z-bestanden of mappen hierheen|Przeciągnij tutaj pliki ZIP/RAR/7z lub foldery|ZIP/RAR/7z dosyalarını veya klasörleri buraya bırakın|Перетащите сюда ZIP/RAR/7z или папки|Перетягніть сюди ZIP/RAR/7z або папки|ZIP/RAR/7zやフォルダーをここにドロップ|ZIP/RAR/7z 파일이나 폴더를 여기에 놓으세요|将 ZIP/RAR/7z 文件或文件夹拖到此处|將 ZIP/RAR/7z 檔案或資料夾拖到此處|اسحب ملفات ZIP/RAR/7z أو المجلدات إلى هنا
Mit Mods _spielen|_Jugar con mods|_Jouer avec les mods|_Gioca con le mod|_Jogar com mods|_Spelen met mods|_Graj z modami|Modlarla _oyna|_Играть с модами|_Грати з модами|MODでプレイ(_P)|모드로 플레이(_P)|使用模组游玩(_P)|使用模組遊玩(_P)|_اللعب مع التعديلات
_Vanilla spielen|Jugar sin _mods|Jouer sans _mods|Gioca senza _mod|Jogar sem _mods|Spelen zonder _mods|Graj _bez modów|Modsuz _oyna|Играть _без модов|Грати _без модів|通常プレイ(_V)|기본 게임 플레이(_V)|原版游玩(_V)|原版遊玩(_V)|اللعب _بدون تعديلات
Mod entfernen|Eliminar mod|Retirer le mod|Rimuovi mod|Remover mod|Mod verwijderen|Usuń mod|Modu kaldır|Удалить мод|Видалити мод|MODを削除|모드 제거|移除模组|移除模組|إزالة التعديل
Rückgängig|Deshacer|Annuler l’action|Annulla modifica|Desfazer|Ongedaan maken|Cofnij|Geri al|Отменить|Скасувати дію|元に戻す|실행 취소|撤销|復原|تراجع
Suchen|Buscar|Rechercher|Cerca|Buscar|Zoeken|Szukaj|Ara|Поиск|Пошук|検索|검색|搜索|搜尋|بحث
Mods durchsuchen|Buscar mods|Rechercher des mods|Cerca mod|Buscar mods|Mods zoeken|Szukaj modów|Mod ara|Поиск модов|Пошук модів|MODを検索|모드 검색|搜索模组|搜尋模組|البحث عن تعديلات
Installierte Mods|Mods instalados|Mods installés|Mod installate|Mods instalados|Geïnstalleerde mods|Zainstalowane mody|Yüklü modlar|Установленные моды|Установлені моди|インストール済みMOD|설치된 모드|已安装的模组|已安裝的模組|التعديلات المثبتة
Mod auswählen|Selecciona un mod|Sélectionnez un mod|Seleziona una mod|Selecione um mod|Selecteer een mod|Wybierz mod|Bir mod seçin|Выберите мод|Виберіть мод|MODを選択|모드 선택|选择模组|選擇模組|اختر تعديلاً
Details & Import|Detalles|Détails|Dettagli|Detalhes|Details|Szczegóły|Ayrıntılar|Сведения|Відомості|詳細|상세 정보|详情|詳細資訊|التفاصيل
_Details|_Detalles|_Détails|_Dettagli|_Detalhes|_Details|_Szczegóły|_Ayrıntılar|_Сведения|_Відомості|詳細(_D)|상세 정보(_D)|详情(_D)|詳細資訊(_D)|_التفاصيل
_Aktivität|_Actividad|_Activité|_Attività|_Atividade|_Activiteit|_Aktywność|_Etkinlik|_Журнал|_Журнал|操作履歴(_A)|활동(_A)|活动(_A)|活動(_A)|_النشاط
_Importliste|_Lista de importación|_Liste d’importation|_Elenco importazioni|_Lista de importação|_Importlijst|_Lista importu|_İçe aktarma listesi|_Список импорта|_Список імпорту|インポート一覧(_I)|가져오기 목록(_I)|导入列表(_I)|匯入清單(_I)|_قائمة الاستيراد
Abbrechen|Cancelar|Annuler|Annulla|Cancelar|Annuleren|Anuluj|İptal|Отмена|Скасувати|キャンセル|취소|取消|取消|إلغاء
Überspringen|Omitir|Ignorer|Salta|Ignorar|Overslaan|Pomiń|Atla|Пропустить|Пропустити|スキップ|건너뛰기|跳过|略過|تخطي
Öffnen|Abrir|Ouvrir|Apri|Abrir|Openen|Otwórz|Aç|Открыть|Відкрити|開く|열기|打开|開啟|فتح
Erneut versuchen|Reintentar|Réessayer|Riprova|Tentar novamente|Opnieuw proberen|Spróbuj ponownie|Yeniden dene|Повторить|Спробувати знову|再試行|다시 시도|重试|重試|إعادة المحاولة
Bereit|Listo|Prêt|Pronto|Pronto|Gereed|Gotowe|Hazır|Готово|Готово|準備完了|준비됨|就绪|就緒|جاهز
Fehler|Error|Erreur|Errore|Erro|Fout|Błąd|Hata|Ошибка|Помилка|エラー|오류|错误|錯誤|خطأ
Hinweise|Avisos|Remarques|Note|Avisos|Opmerkingen|Uwagi|Notlar|Примечания|Примітки|注意事項|안내|提示|提示|ملاحظات
Pausiert|En pausa|En pause|In pausa|Pausado|Gepauzeerd|Wstrzymany|Duraklatıldı|Приостановлен|Призупинено|一時停止|일시 중지|已暂停|已暫停|متوقف مؤقتاً
Aktiv|Activo|Actif|Attivo|Ativo|Actief|Aktywny|Etkin|Активен|Активний|有効|활성|已启用|已啟用|نشط
Abgeschlossen|Completado|Terminé|Completato|Concluído|Voltooid|Ukończono|Tamamlandı|Завершено|Завершено|完了|완료|已完成|已完成|مكتمل
Fehlgeschlagen|Fallido|Échec|Non riuscito|Falhou|Mislukt|Niepowodzenie|Başarısız|Ошибка|Не вдалося|失敗|실패|失败|失敗|فشل
Abgebrochen|Cancelado|Annulé|Annullato|Cancelado|Geannuleerd|Anulowano|İptal edildi|Отменено|Скасовано|キャンセル済み|취소됨|已取消|已取消|ملغى
Unterbrochen|Interrumpido|Interrompu|Interrotto|Interrompido|Onderbroken|Przerwano|Kesildi|Прервано|Перервано|中断|중단됨|已中断|已中斷|انقطع
Wartet|En cola|En attente|In coda|Na fila|In wachtrij|W kolejce|Sırada|В очереди|У черзі|待機中|대기 중|排队中|佇列中|في الانتظار
Prüfung|Verificando|Vérification|Verifica|Verificando|Controleren|Weryfikacja|Doğrulanıyor|Проверка|Перевірка|確認中|확인 중|正在校验|正在驗證|جارٍ التحقق
In Arbeit|En curso|En cours|In corso|Em andamento|Bezig|W toku|İşleniyor|Выполняется|Виконується|処理中|진행 중|处理中|處理中|قيد التنفيذ
Schon vorhanden|Ya instalado|Déjà installé|Già installato|Já instalado|Al geïnstalleerd|Już zainstalowany|Zaten yüklü|Уже установлен|Уже встановлено|インストール済み|이미 설치됨|已安装|已安裝|مثبت بالفعل
Doppelt|Duplicado|Doublon|Duplicato|Duplicado|Dubbel|Duplikat|Yinelenen|Дубликат|Дублікат|重複|중복|重复|重複|مكرر
Konflikt|Conflicto|Conflit|Conflitto|Conflito|Conflict|Konflikt|Çakışma|Конфликт|Конфлікт|競合|충돌|冲突|衝突|تعارض
Installiert|Instalado|Installé|Installato|Instalado|Geïnstalleerd|Zainstalowano|Yüklendi|Установлен|Установлено|インストール済み|설치됨|已安装|已安裝|مثبت
Ungueltig|No válido|Non valide|Non valido|Inválido|Ongeldig|Nieprawidłowy|Geçersiz|Недопустимо|Недійсне|無効|유효하지 않음|无效|無效|غير صالح
Ausgelassen|Omitido|Ignoré|Saltato|Ignorado|Overgeslagen|Pominięto|Atlandı|Пропущено|Пропущено|スキップ済み|건너뜀|已跳过|已略過|تم التخطي
Heller Modus|Claro|Clair|Chiaro|Claro|Licht|Jasny|Açık|Светлая|Світла|ライト|밝게|浅色|淺色|فاتح
Dunkler Modus|Oscuro|Sombre|Scuro|Escuro|Donker|Ciemny|Koyu|Тёмная|Темна|ダーク|어둡게|深色|深色|داكن
Wie Windows|Usar ajuste de Windows|Selon Windows|Come Windows|Seguir o Windows|Windows volgen|Według Windows|Windows ayarı|Как в Windows|Як у Windows|Windowsに合わせる|Windows 설정 따르기|跟随 Windows|跟隨 Windows|حسب إعداد Windows
Alle Mods als ZIP exportieren…|Exportar mods como ZIP…|Exporter les mods en ZIP…|Esporta mod in ZIP…|Exportar mods em ZIP…|Mods als ZIP exporteren…|Eksportuj mody do ZIP…|Modları ZIP olarak dışa aktar…|Экспорт модов в ZIP…|Експорт модів у ZIP…|MODをZIPでエクスポート…|모드를 ZIP으로 내보내기…|将模组导出为 ZIP…|將模組匯出為 ZIP…|تصدير التعديلات بصيغة ZIP…
GameBanana-Link öffnen…|Abrir enlace de GameBanana…|Ouvrir un lien GameBanana…|Apri link GameBanana…|Abrir link do GameBanana…|GameBanana-link openen…|Otwórz link GameBanana…|GameBanana bağlantısı aç…|Открыть ссылку GameBanana…|Відкрити посилання GameBanana…|GameBananaリンクを開く…|GameBanana 링크 열기…|打开 GameBanana 链接…|開啟 GameBanana 連結…|فتح رابط GameBanana…
Manager-Link zur Datei kopieren|Copiar enlace del gestor|Copier le lien du gestionnaire|Copia link del gestore|Copiar link do gerenciador|Managerlink kopiëren|Kopiuj link menedżera|Yönetici bağlantısını kopyala|Копировать ссылку менеджера|Копіювати посилання менеджера|マネージャーリンクをコピー|매니저 링크 복사|复制管理器链接|複製管理器連結|نسخ رابط المدير
GameBanana-Updates prüfen|Buscar actualizaciones de GameBanana|Vérifier les mises à jour GameBanana|Controlla aggiornamenti GameBanana|Verificar atualizações do GameBanana|GameBanana-updates controleren|Sprawdź aktualizacje GameBanana|GameBanana güncellemelerini denetle|Проверить обновления GameBanana|Перевірити оновлення GameBanana|GameBananaの更新を確認|GameBanana 업데이트 확인|检查 GameBanana 更新|檢查 GameBanana 更新|التحقق من تحديثات GameBanana
Bibliothek vollständig prüfen|Verificar biblioteca|Vérifier la bibliothèque|Verifica libreria|Verificar biblioteca|Bibliotheek controleren|Sprawdź bibliotekę|Kütüphaneyi doğrula|Проверить библиотеку|Перевірити бібліотеку|ライブラリを検証|라이브러리 검사|校验模组库|驗證模組庫|التحقق من المكتبة
Protokolle öffnen|Abrir registros|Ouvrir les journaux|Apri registri|Abrir registros|Logboeken openen|Otwórz dzienniki|Günlükleri aç|Открыть журналы|Відкрити журнали|ログを開く|로그 열기|打开日志|開啟記錄|فتح السجلات
Pausiert installieren|Instalar en pausa|Installer en pause|Installa in pausa|Instalar pausado|Gepauzeerd installeren|Zainstaluj jako wstrzymany|Duraklatılmış olarak yükle|Установить без активации|Установити без активації|無効のままインストール|비활성 상태로 설치|安装但不启用|安裝但不啟用|تثبيت دون تفعيل
Konfliktpartner ersetzen|Reemplazar mods en conflicto|Remplacer les mods en conflit|Sostituisci mod in conflitto|Substituir mods em conflito|Conflicterende mods vervangen|Zastąp kolidujące mody|Çakışan modları değiştir|Заменить конфликтующие моды|Замінити конфліктні моди|競合するMODを置換|충돌 모드 교체|替换冲突的模组|取代衝突的模組|استبدال التعديلات المتعارضة
Dateien für Auswahl…|Elegir archivos…|Choisir les fichiers…|Scegli file…|Escolher arquivos…|Bestanden kiezen…|Wybierz pliki…|Dosya seç…|Выбрать файлы…|Вибрати файли…|ファイルを選択…|파일 선택…|选择文件…|選擇檔案…|اختيار الملفات…
Download einreihen|Descargar|Télécharger|Scarica|Baixar|Downloaden|Pobierz|İndir|Скачать|Завантажити|ダウンロード|다운로드|下载|下載|تنزيل
Quellseite ↗|Página original ↗|Page d’origine ↗|Pagina originale ↗|Página original ↗|Bronpagina ↗|Strona źródłowa ↗|Kaynak sayfa ↗|Страница мода ↗|Сторінка мода ↗|配布ページ ↗|원본 페이지 ↗|来源页面 ↗|來源頁面 ↗|صفحة المصدر ↗
Auswahl installieren…|Instalar selección…|Installer la sélection…|Installa selezione…|Instalar seleção…|Selectie installeren…|Zainstaluj wybrane…|Seçimi yükle…|Установить выбранное…|Установити вибране…|選択項目をインストール…|선택 항목 설치…|安装所选项…|安裝選取項目…|تثبيت المحدد…
Auswahl abbrechen|Cancelar selección|Annuler la sélection|Annulla selezione|Cancelar seleção|Selectie annuleren|Anuluj wybrane|Seçimi iptal et|Отменить выбранное|Скасувати вибране|選択項目をキャンセル|선택 항목 취소|取消所选项|取消選取項目|إلغاء المحدد
Alle Charaktere|Todos los personajes|Tous les personnages|Tutti i personaggi|Todos os personagens|Alle personages|Wszystkie postacie|Tüm karakterler|Все персонажи|Усі персонажі|すべてのキャラクター|모든 캐릭터|所有角色|所有角色|جميع الشخصيات
Zuletzt aktualisiert|Actualizados recientemente|Mis à jour récemment|Aggiornati di recente|Atualizados recentemente|Recent bijgewerkt|Ostatnio zaktualizowane|Son güncellenenler|Недавно обновлённые|Нещодавно оновлені|最近更新|최근 업데이트|最近更新|最近更新|المحدثة مؤخراً
Neueste|Más recientes|Plus récents|Più recenti|Mais recentes|Nieuwste|Najnowsze|En yeniler|Новые|Нові|新着|최신|最新|最新|الأحدث
Meiste Downloads|Más descargados|Plus téléchargés|Più scaricati|Mais baixados|Meest gedownload|Najczęściej pobierane|En çok indirilenler|Самые скачиваемые|Найпопулярніші завантаження|ダウンロード数順|다운로드 순|下载最多|下載最多|الأكثر تنزيلاً
Meiste Likes|Más populares|Plus appréciés|Più apprezzati|Mais curtidos|Meest gewaardeerd|Najwięcej polubień|En çok beğenilenler|Самые популярные|Найбільше вподобань|人気順|좋아요 순|点赞最多|按讚最多|الأكثر إعجاباً
Keine Variante vorausgewählt.|Ningún archivo seleccionado.|Aucun fichier sélectionné.|Nessun file selezionato.|Nenhum arquivo selecionado.|Geen bestand geselecteerd.|Nie wybrano pliku.|Dosya seçilmedi.|Файл не выбран.|Файл не вибрано.|ファイル未選択。|선택한 파일이 없습니다.|尚未选择文件。|尚未選擇檔案。|لم يُحدد ملف.
Dateivariante ausdrücklich auswählen:|Elige un archivo:|Choisissez un fichier :|Scegli un file:|Escolha um arquivo:|Kies een bestand:|Wybierz plik:|Bir dosya seçin:|Выберите файл:|Виберіть файл:|ファイルを選択：|파일 선택:|选择文件：|選擇檔案：|اختر ملفاً:
Abhängigkeiten & Installation|Dependencias e instalación|Dépendances et installation|Dipendenze e installazione|Dependências e instalação|Afhankelijkheden en installatie|Zależności i instalacja|Bağımlılıklar ve kurulum|Зависимости и установка|Залежності та встановлення|依存関係とインストール|필수 항목 및 설치|依赖项与安装|相依項目與安裝|المتطلبات والتثبيت
Schließen (Esc)|Cerrar (Esc)|Fermer (Esc)|Chiudi (Esc)|Fechar (Esc)|Sluiten (Esc)|Zamknij (Esc)|Kapat (Esc)|Закрыть (Esc)|Закрити (Esc)|閉じる (Esc)|닫기 (Esc)|关闭 (Esc)|關閉 (Esc)|إغلاق (Esc)
‹ Zurück|‹ Anterior|‹ Précédent|‹ Precedente|‹ Anterior|‹ Vorige|‹ Poprzedni|‹ Önceki|‹ Назад|‹ Назад|‹ 前へ|‹ 이전|‹ 上一张|‹ 上一張|‹ السابق
Weiter ›|Siguiente ›|Suivant ›|Successivo ›|Próximo ›|Volgende ›|Następny ›|Sonraki ›|Далее ›|Далі ›|次へ ›|다음 ›|下一张 ›|下一張 ›|التالي ›
OpenSmash verbinden|Conectar OpenSmash|Connecter OpenSmash|Collega OpenSmash|Conectar OpenSmash|OpenSmash verbinden|Połącz OpenSmash|OpenSmash bağla|Подключить OpenSmash|Підключити OpenSmash|OpenSmashを接続|OpenSmash 연결|连接 OpenSmash|連接 OpenSmash|ربط OpenSmash
Ordner auswaehlen…|Elegir carpeta…|Choisir un dossier…|Scegli cartella…|Escolher pasta…|Map kiezen…|Wybierz folder…|Klasör seç…|Выбрать папку…|Вибрати папку…|フォルダーを選択…|폴더 선택…|选择文件夹…|選擇資料夾…|اختيار مجلد…
Pfad pruefen|Comprobar ruta|Vérifier le chemin|Verifica percorso|Verificar caminho|Pad controleren|Sprawdź ścieżkę|Yolu denetle|Проверить путь|Перевірити шлях|パスを確認|경로 확인|检查路径|檢查路徑|التحقق من المسار
Verbinden und oeffnen|Conectar y abrir|Connecter et ouvrir|Collega e apri|Conectar e abrir|Verbinden en openen|Połącz i otwórz|Bağla ve aç|Подключить и открыть|Підключити й відкрити|接続して開く|연결하고 열기|连接并打开|連接並開啟|ربط وفتح
Schliessen|Cerrar|Fermer|Chiudi|Fechar|Sluiten|Zamknij|Kapat|Закрыть|Закрити|閉じる|닫기|关闭|關閉|إغلاق
Manager oeffnen|Abrir gestor|Ouvrir le gestionnaire|Apri gestore|Abrir gerenciador|Manager openen|Otwórz menedżera|Yöneticiyi aç|Открыть менеджер|Відкрити менеджер|マネージャーを開く|매니저 열기|打开管理器|開啟管理器|فتح المدير
Deine Mods. Dein Spiel.|Tus mods. Tu juego.|Vos mods. Votre jeu.|Le tue mod. Il tuo gioco.|Seus mods. Seu jogo.|Jouw mods. Jouw spel.|Twoje mody. Twoja gra.|Senin modların. Senin oyunun.|Ваши моды. Ваша игра.|Ваші моди. Ваша гра.|あなたのMOD。あなたのゲーム。|나만의 모드. 나만의 게임.|你的模组。你的游戏。|你的模組。你的遊戲。|تعديلاتك. لعبتك.
{0} Mods · {1} aktiv|{0} mods · {1} activos|{0} mods · {1} actifs|{0} mod · {1} attive|{0} mods · {1} ativos|{0} mods · {1} actief|Mody: {0} · aktywne: {1}|{0} mod · {1} etkin|Модов: {0} · активно: {1}|Модів: {0} · активних: {1}|MOD {0} 件 · 有効 {1} 件|모드 {0}개 · 활성 {1}개|{0} 个模组 · {1} 个已启用|{0} 個模組 · {1} 個已啟用|{0} تعديل · {1} نشط
{0} Downloads · {1} in Arbeit.|{0} descargas · {1} en curso.|{0} téléchargements · {1} en cours.|{0} download · {1} in corso.|{0} downloads · {1} em andamento.|{0} downloads · {1} bezig.|Pobrania: {0} · w toku: {1}.|{0} indirme · {1} sürüyor.|Загрузок: {0} · выполняется: {1}.|Завантажень: {0} · виконується: {1}.|ダウンロード {0} 件 · 処理中 {1} 件|다운로드 {0}개 · 진행 중 {1}개|{0} 项下载 · {1} 项进行中|{0} 項下載 · {1} 項進行中|{0} تنزيل · {1} قيد التنفيذ.
Noch keine Mods|Sin mods todavía|Aucun mod pour le moment|Ancora nessuna mod|Nenhum mod ainda|Nog geen mods|Brak modów|Henüz mod yok|Модов пока нет|Модів поки немає|MODはまだありません|아직 모드가 없습니다|暂无模组|尚無模組|لا توجد تعديلات بعد
Noch keine Downloads. Mods findest du unter Entdecken.|Sin descargas. Busca mods en Descubrir.|Aucun téléchargement. Trouvez des mods dans Découvrir.|Nessun download. Cerca mod in Scopri.|Nenhum download. Encontre mods em Descobrir.|Nog geen downloads. Vind mods in Ontdekken.|Brak pobrań. Znajdź mody w Odkrywaj.|İndirme yok. Keşfet bölümünde mod bulun.|Загрузок нет. Найдите моды в разделе «Обзор».|Завантажень немає. Знайдіть моди в розділі «Огляд».|ダウンロードはありません。「見つける」でMODを探せます。|다운로드가 없습니다. 탐색에서 모드를 찾아보세요.|暂无下载。请到“发现”查找模组。|尚無下載。請到「探索」尋找模組。|لا توجد تنزيلات. ابحث عن تعديلات في «استكشاف».
Originalbild wird geladen…|Cargando imagen…|Chargement de l’image…|Caricamento immagine…|Carregando imagem…|Afbeelding laden…|Ładowanie obrazu…|Görsel yükleniyor…|Загрузка изображения…|Завантаження зображення…|画像を読み込み中…|이미지 불러오는 중…|正在加载原图…|正在載入原圖…|جارٍ تحميل الصورة…
Katalog wird geladen…|Cargando catálogo…|Chargement du catalogue…|Caricamento catalogo…|Carregando catálogo…|Catalogus laden…|Ładowanie katalogu…|Katalog yükleniyor…|Загрузка каталога…|Завантаження каталогу…|カタログを読み込み中…|목록 불러오는 중…|正在加载目录…|正在載入目錄…|جارٍ تحميل القائمة…
Keine Ergebnisse. Anderen Suchbegriff versuchen.|Sin resultados. Prueba otra búsqueda.|Aucun résultat. Essayez un autre terme.|Nessun risultato. Prova un altro termine.|Sem resultados. Tente outro termo.|Geen resultaten. Probeer een andere zoekterm.|Brak wyników. Spróbuj innego hasła.|Sonuç yok. Başka bir sözcük deneyin.|Нет результатов. Измените запрос.|Немає результатів. Змініть запит.|結果がありません。別のキーワードをお試しください。|결과가 없습니다. 다른 검색어를 입력하세요.|没有结果。请尝试其他关键词。|沒有結果。請嘗試其他關鍵字。|لا توجد نتائج. جرّب عبارة بحث أخرى.
Wirksam beim nächsten Spielstart.|Se aplica al volver a iniciar el juego.|Applicable au prochain lancement du jeu.|Si applica al prossimo avvio del gioco.|Aplicado na próxima inicialização do jogo.|Geldt bij de volgende spelstart.|Zadziała przy następnym uruchomieniu gry.|Oyun yeniden başlatıldığında uygulanır.|Применится при следующем запуске игры.|Застосується під час наступного запуску гри.|次回のゲーム起動時に適用されます。|다음 게임 실행 시 적용됩니다.|下次启动游戏时生效。|下次啟動遊戲時生效。|يسري عند تشغيل اللعبة مجدداً.
Auswahl gespeichert|Selección guardada|Sélection enregistrée|Selezione salvata|Seleção salva|Selectie opgeslagen|Zapisano wybór|Seçim kaydedildi|Выбор сохранён|Вибір збережено|選択を保存しました|선택 저장됨|已保存选择|已儲存選擇|تم حفظ الاختيار
Vorgang läuft…|Procesando…|Traitement en cours…|Operazione in corso…|Processando…|Bezig…|Przetwarzanie…|İşleniyor…|Выполняется…|Виконується…|処理中…|처리 중…|处理中…|處理中…|جارٍ التنفيذ…
Modmanager wird vorbereitet…|Preparando gestor…|Préparation du gestionnaire…|Preparazione gestore…|Preparando gerenciador…|Manager voorbereiden…|Przygotowywanie menedżera…|Yönetici hazırlanıyor…|Подготовка менеджера…|Підготовка менеджера…|マネージャーを準備中…|매니저 준비 중…|正在准备管理器…|正在準備管理器…|جارٍ إعداد المدير…
Alle Downloads löschen…|Eliminar todas las descargas…|Supprimer tous les téléchargements…|Elimina tutti i download…|Excluir todos os downloads…|Alle downloads verwijderen…|Usuń wszystkie pobrania…|Tüm indirmeleri sil…|Удалить все загрузки…|Видалити всі завантаження…|すべてのダウンロードを削除…|모든 다운로드 삭제…|删除所有下载…|刪除所有下載…|حذف جميع التنزيلات…
Alle löschen|Eliminar todo|Tout supprimer|Elimina tutto|Excluir tudo|Alles verwijderen|Usuń wszystko|Tümünü sil|Удалить всё|Видалити все|すべて削除|모두 삭제|全部删除|全部刪除|حذف الكل
Datei speichern…|Guardar archivo…|Enregistrer le fichier…|Salva file…|Salvar arquivo…|Bestand opslaan…|Zapisz plik…|Dosyayı kaydet…|Сохранить файл…|Зберегти файл…|ファイルを保存…|파일 저장…|保存文件…|儲存檔案…|حفظ الملف…
 · Nur Download| · Solo descarga| · Téléchargement seul| · Solo download| · Apenas download| · Alleen downloaden| · Tylko pobieranie| · Yalnızca indirme| · Только загрузка| · Лише завантаження| · ダウンロードのみ| · 다운로드만| · 仅下载| · 僅下載| · تنزيل فقط
 · Gesperrt| · Restringido| · Accès restreint| · Accesso limitato| · Restrito| · Beperkt| · Zablokowane| · Kısıtlı| · Ограничено| · Обмежено| · 制限あり| · 제한됨| · 受限| · 受限| · مقيّد
"""


def main():
    result = {}
    for row in ROWS.splitlines():
        if not row:
            continue
        source, *values = row.split("|")
        if len(values) != len(LANGUAGES):
            raise ValueError(f"Wrong column count for {source}: {len(values)}")
        result[source] = dict(zip(LANGUAGES, values))
    # Identical short status messages and tooltips share reviewed vocabulary.
    aliases = {
        "Bereit.": ("Bereit", "."),
        "Dein OpenSmash verbinden": ("OpenSmash verbinden", ""),
        "Vorherige Seite": ("‹ Zurück", ""),
        "Vorheriges Vorschaubild": ("‹ Zurück", ""),
        "Naechste Seite": ("Weiter ›", ""),
        "Naechstes Vorschaubild": ("Weiter ›", ""),
        "GameBanana-Link öffnen": ("GameBanana-Link öffnen…", ""),
        "Auswaehlen …": ("Ordner auswaehlen…", ""),
    }
    for source, (target, suffix) in aliases.items():
        result[source] = {lang: text + suffix for lang, text in result[target].items()}
    result["Details"] = {
        language: text.replace("_", "") for language, text in result["_Details"].items()
    }
    for key in ("Modliste teilen", "Modliste importieren"):
        result[key] = {
            language: text.rstrip("…") for language, text in result[key + "…"].items()
        }
    result["Modliste gespeichert."] = {
        language: text + "."
        for language, text in result["Modliste gespeichert"].items()
    }
    result["Titelbild auswählen…"] = {
        language: text + "…" for language, text in result["Titelbild auswählen"].items()
    }
    extra = {
        "Deine Bibliothek ist noch leer.\nFüge oben deine erste Mod hinzu.": [
            "Tu biblioteca está vacía.\nAñade tu primer mod arriba.",
            "Votre bibliothèque est vide.\nAjoutez votre premier mod ci-dessus.",
            "La libreria è vuota.\nAggiungi la prima mod in alto.",
            "Sua biblioteca está vazia.\nAdicione seu primeiro mod acima.",
            "Je bibliotheek is leeg.\nVoeg hierboven je eerste mod toe.",
            "Biblioteka jest pusta.\nDodaj swój pierwszy mod powyżej.",
            "Kütüphaneniz boş.\nYukarıdan ilk modunuzu ekleyin.",
            "Ваша библиотека пуста.\nДобавьте первый мод сверху.",
            "Ваша бібліотека порожня.\nДодайте перший мод угорі.",
            "ライブラリは空です。\n上から最初のMODを追加してください。",
            "라이브러리가 비어 있습니다.\n위에서 첫 모드를 추가하세요.",
            "模组库为空。\n请在上方添加第一个模组。",
            "模組庫是空的。\n請在上方新增第一個模組。",
            "مكتبتك فارغة.\nأضف أول تعديل من الأعلى.",
        ],
        "Keine passenden Mods gefunden.\nVersuche einen anderen Suchbegriff.": [
            "No hay mods coincidentes.\nPrueba otra búsqueda.",
            "Aucun mod correspondant.\nEssayez un autre terme.",
            "Nessuna mod corrispondente.\nProva un altro termine.",
            "Nenhum mod encontrado.\nTente outro termo.",
            "Geen passende mods gevonden.\nProbeer een andere zoekterm.",
            "Nie znaleziono pasujących modów.\nSpróbuj innego hasła.",
            "Eşleşen mod bulunamadı.\nBaşka bir sözcük deneyin.",
            "Подходящих модов нет.\nИзмените поисковый запрос.",
            "Відповідних модів немає.\nЗмініть пошуковий запит.",
            "一致するMODがありません。\n別のキーワードをお試しください。",
            "일치하는 모드가 없습니다.\n다른 검색어를 입력하세요.",
            "没有匹配的模组。\n请尝试其他关键词。",
            "沒有符合的模組。\n請嘗試其他關鍵字。",
            "لا توجد تعديلات مطابقة.\nجرّب عبارة بحث أخرى.",
        ],
        "Installiert den Manager für dein Benutzerkonto. Deine Mods und Spieldaten bleiben erhalten.": [
            "Instala el gestor para tu cuenta. Se conservan tus mods y datos del juego.",
            "Installe le gestionnaire pour votre compte. Vos mods et données de jeu sont conservés.",
            "Installa il gestore per il tuo account. Mod e dati di gioco vengono conservati.",
            "Instala o gerenciador para sua conta. Seus mods e dados do jogo são preservados.",
            "Installeert de manager voor je account. Je mods en spelgegevens blijven behouden.",
            "Instaluje menedżera dla Twojego konta. Mody i dane gry zostaną zachowane.",
            "Yöneticiyi hesabınıza yükler. Modlarınız ve oyun verileriniz korunur.",
            "Установит менеджер для вашей учётной записи. Моды и игровые данные сохранятся.",
            "Установить менеджер для вашого облікового запису. Моди та ігрові дані збережуться.",
            "このユーザー用にマネージャーをインストールします。MODとゲームデータは保持されます。",
            "현재 계정에 매니저를 설치합니다. 모드와 게임 데이터는 유지됩니다.",
            "为当前账户安装管理器。模组和游戏数据将予以保留。",
            "為目前帳戶安裝管理器。模組及遊戲資料將保留。",
            "يثبّت المدير لحسابك. تُحفظ تعديلاتك وبيانات اللعبة.",
        ],
        "Der Manager ist eingerichtet. Deine Mods und Spieldaten bleiben erhalten.": [
            "El gestor está listo. Tus mods y datos del juego se conservan.",
            "Le gestionnaire est prêt. Vos mods et données de jeu sont conservés.",
            "Il gestore è pronto. Mod e dati di gioco sono conservati.",
            "O gerenciador está pronto. Seus mods e dados do jogo foram preservados.",
            "De manager is klaar. Je mods en spelgegevens blijven behouden.",
            "Menedżer jest gotowy. Mody i dane gry zostały zachowane.",
            "Yönetici hazır. Modlarınız ve oyun verileriniz korundu.",
            "Менеджер установлен. Моды и игровые данные сохранены.",
            "Менеджер установлено. Моди та ігрові дані збережено.",
            "準備が完了しました。MODとゲームデータは保持されています。",
            "매니저가 준비되었습니다. 모드와 게임 데이터는 유지됩니다.",
            "管理器已就绪。模组和游戏数据已保留。",
            "管理器已就緒。模組及遊戲資料已保留。",
            "المدير جاهز. تم حفظ تعديلاتك وبيانات اللعبة.",
        ],
    }
    for key, values in extra.items():
        assert len(values) == len(LANGUAGES)
        result[key] = dict(zip(LANGUAGES, values))
    path = Path(__file__).resolve().parent / "installer/workflow_translations.json"
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {len(result)} workflow translations in {len(LANGUAGES)} additional languages"
    )


if __name__ == "__main__":
    main()
