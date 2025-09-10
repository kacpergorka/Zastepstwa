# POLITYKA PRYWATNOŚCI

**Niniejsza Polityka Prywatności** („Polityka”) określa zasady gromadzenia, przetwarzania i przechowywania danych przez bota Discord **Zastępstwa#9138 (ID: 1278769348822962196)** („Bot”), udostępnianego przez **Kacpra Górkę** („Właściciel”).

Korzystając z Bota, Użytkownik („Użytkownik”) akceptuje postanowienia niniejszej Polityki. W przypadku braku zgody Użytkownik powinien natychmiast zaprzestać korzystania z Bota.

Administratorem danych osobowych przetwarzanych przez Bota jest [Kacper Górka](kontakt@kacpergorka.com).  
Polityka dotyczy danych przetwarzanych przez hostowaną instancję Bota. Przetwarzanie danych przez platformę Discord odbywa się na zasadach określonych przez [Discorda](https://discord.com) i jego [politykę prywatności](https://discord.com/privacy).

## §1. Jakie dane są gromadzone
`§1.1.` **Dane identyfikacyjne z Discorda** – identyfikatory użytkowników, serwerów i kanałów tekstowych oraz nazwy użytkowników.  
`§1.2.` **Dane konfiguracyjne serwera** – wybrane podczas konfiguracji filtry (klasy, nauczyciele) i kanały tekstowe, statystyki zastępstw nauczycieli, licznik wysłanych zastępstw i znacznik ostatniego podsumowania rocznego statystyk.   
`§1.3.` **Treść poleceń i użycie Bota** – argumenty wywołań poleceń oraz dane techniczne zapisywane w logach.  
`§1.4.` **Dane zewnętrzne** – Bot okresowo pobiera treść ze strony wskazanej w pliku konfiguracyjnym i publikuje jej przetworzoną treść w kanałach Discord. Dane pochodzące ze źródeł zewnętrznych (np. nazwy nauczycieli) mogą identyfikować osoby fizyczne. Bot normalizuje i indeksuje takie dane w celu dopasowania i tworzenia statystyk (zob. `§2.1.` i `§9.2.`).  
`§1.5.` **Metadane konfiguracyjne i predefiniowane listy** – Plik konfiguracyjny zawiera dodatkowe informacje techniczne, takie jak numer wersji oprogramowania, data zakończenia roku szkolnego oraz domyślne kodowanie strony wykorzystywanej do pobierania informacji o zastępstwach. Ponadto przechowuje predefiniowane listy klas i listy nauczycieli przypisane do poszczególnych szkół. Lista nauczycieli może zawierać imiona i nazwiska (lub inicjały), które są przetwarzane w celu dopasowania danych zewnętrznych oraz tworzenia statystyk zastępstw (zob. `§9.2.` i `§2.4.`).  
`§1.6.` **Dane administracyjne** – przy dołączeniu Bota na serwer próba wysłania wiadomości prywatnej do użytkownika, który go dodał, ustalonego na podstawie logów audytu.  
`§1.7.` Dane pochodzą bezpośrednio od Użytkowników podczas zawierania interakcji z Botem, z [API Discord](https://discord.com/developers/docs/reference) (ID, metadane serwera/kanałów) oraz z adresu URL wskazanego w pliku konfiguracyjnym (dane zewnętrzne publikowane na serwerze).

## §2. Cele przetwarzania danych
`§2.1.` **Świadczenie funkcjonalności Bota** – powiadomienia o zastępstwach, statystyki i filtrowanie treści.  
`§2.2.` **Diagnostyka i bezpieczeństwo** – tworzenie logów w celu wykrywania błędów, nadużyć i zapewnienia stabilności.  
`§2.3.` **Komunikacja administracyjna** – wysyłanie wiadomości informacyjnych administratorom serwera.  
`§2.4.` Podstawy prawne przetwarzania danych:  
– art. 6 ust. 1 lit. b RODO — przetwarzanie jest niezbędne do wykonania usługi (świadczenia funkcji Bota) na rzecz Użytkownika;  
– art. 6 ust. 1 lit. f RODO — prawnie uzasadniony interes Właściciela (np. diagnostyka, wykrywanie nadużyć, zapewnienie bezpieczeństwa i stabilności działania Bota, a także przetwarzanie danych z zewnętrznych źródeł w celu publikacji powiadomień i statystyk).

## §3. Udostępnianie danych
`§3.1.` Dane nie są sprzedawane ani przekazywane podmiotom trzecim w celach komercyjnych.  
`§3.2.` Dane mogą być ujawnione wyłącznie na żądanie organów ścigania lub zgodnie z obowiązującym prawem; w celu ochrony praw, bezpieczeństwa lub przeciwdziałania nadużyciom.  
`§3.3.` Role i kategorie odbiorców:  
– Właściciel jest administratorem danych w zakresie przetwarzania wykonywanego przez Bota.  
– Platforma Discord działa równolegle jako administrator/przetwarzający danych w kontekście świadczenia usługi platformy (dla użytkowników z EEA kontrolerem jest Discord Netherlands BV; dla pozostałych użytkowników kontrolerem jest Discord Inc.). Dane przesyłane przez Bota do Discorda podlegają również [polityce prywatności Discorda](https://discord.com/privacy).  
`§3.4.` Dane mogą być przetwarzane poza EOG przez niezależnych administratorów (np. Discord), zgodnie z ich mechanizmami transferu Standard Contractual Clauses lub inne środki zgodne z prawem UE. Właściciel co do zasady przetwarza dane na serwerach zlokalizowanych w EOG, chyba że charakter usługi lub wybrani dostawcy techniczni wymagają inaczej.  
`§3.5.` Właściciel może korzystać z dostawców usług na terenie UE (np. hosting, backup, monitoring błędów) jako podmiotów przetwarzających. Podmioty te przetwarzają dane wyłącznie na polecenie Właściciela i na podstawie umów zapewniających wymagany poziom ochrony.

## §4. Przechowywanie danych
`§4.1.` Pliki konfiguracyjne (`config.json` oraz `Resources/<server_id>.json`) i logi (`Logs/console.log`) są przechowywane lokalnie na serwerze, na którym działa Bot.  
`§4.2.` Dane przechowywane są tak długo, jak jest to konieczne do świadczenia funkcji Bota lub wymagane prawem.  
`§4.3.` Konfiguracja serwera zapisana w pliku `config.json` oraz odrębna konfiguracja `Resources/<server_id>.json` są usuwane niezwłocznie po usunięciu Bota z serwera Discord.  
`§4.4.` Właściciel zobowiązuje się do usuwania logów starszych niż 6 miesięcy oraz do okresowego przeglądu logów celem usunięcia danych, które nie są już potrzebne do celów wymienionych w `§2`. W wyjątkowych, uzasadnionych przypadkach (np. zapewnienie bezpieczeństwa, diagnostyka błędów, wykrywanie nadużyć lub prowadzenie dokumentacji technicznej) niektóre logi mogą być przechowywane dłużej; zostaną one jednak ograniczone do niezbędnego zakresu i zabezpieczone.  
`§4.5.` Niepodanie, usunięcie danych lub ograniczenie uprawnień (np. zablokowanie wiadomości prywatnych, brak uprawnień do wysyłania wiadomości) może spowodować, że niektóre funkcje Bota nie będą dostępne dla Użytkownika lub dla jego serwera.

## §5. Bezpieczeństwo
`§5.1.` Właściciel stosuje środki organizacyjne i techniczne mające na celu ochronę danych, m.in. ograniczenie dostępu do plików konfiguracyjnych, szyfrowanie transmisji danych oraz regularne aktualizacje oprogramowania.  
`§5.2.` Token Bota przechowywany w pliku `config.json` jest traktowany jako poufny i nie powinien być publikowany.  
`§5.3.` Pomimo stosowanych zabezpieczeń, Właściciel nie może zagwarantować pełnej ochrony przed nieautoryzowanym dostępem.

## §6. Prawa Użytkowników
`§6.1.` Użytkownik ma prawo do dostępu do swoich danych, sprostowania danych, usunięcia danych („prawo do bycia zapomnianym”), ograniczenia przetwarzania, przenoszenia danych (w zakresie możliwym technicznie).  
`§6.2.` Użytkownik ma prawo do wniesienia sprzeciwu wobec przetwarzania danych na podstawie art. 6 ust. 1 lit. f RODO.  
`§6.3.` Żądania realizacji praw (np. dostęp, sprostowanie, usunięcie, ograniczenie, przeniesienie danych) można zgłaszać na adres kontakt@kacpergorka.com. W zgłoszeniu należy podać identyfikator serwera Discord i krótki opis żądanej operacji. W przypadku żądania usunięcia danych serwera Właściciel usunie odpowiednie pliki (`Resources/<server_id>.json` oraz powiązane wpisy w `config.json`) w terminie do 30 dni.  
`§6.4.` Wnioski o realizację praw (np. dostęp, sprostowanie, usunięcie) będą rozpatrywane bez zbędnej zwłoki, nie później niż w terminie jednego miesiąca od otrzymania żądania. W wyjątkowych, uzasadnionych przypadkach termin ten może zostać przedłużony o kolejne dwa miesiące, o czym Użytkownik zostanie poinformowany wraz z uzasadnieniem.

## §7. Powiadomienia i automatyczne wzmianki
`§7.1.` Bot może wysyłać wzmianki `@everyone`, jeśli ma odpowiednie uprawnienia na serwerze. Administratorzy powinni skonfigurować dostęp zgodnie z własnymi preferencjami.  
`§7.2.` Bot może wysyłać wiadomości prywatne do użytkownika, który go dodał, w celu przekazania instrukcji i informacji konfiguracyjnych.

## §8. Zmiany Polityki
`§8.1.` Właściciel może zmieniać postanowienia Polityki.  
`§8.2.` O istotnych zmianach Użytkownicy będą informowani poprzez repozytorium GitHub oraz na oficjalnym [serwerze Discord](https://discord.gg/f53qc2yZW7).

## §9. Prawa związane z RODO
`§9.1.` Użytkownik ma prawo wnieść skargę do organu nadzorczego – Prezesa Urzędu Ochrony Danych Osobowych (UODO), jeżeli uzna, że przetwarzanie jego danych narusza przepisy prawa.  
`§9.2.` Bot tworzy zagregowane statystyki dotyczące nauczycieli (np. liczba zarejestrowanych zastępstw przypisanych do konkretnej nazwy nauczyciela), które są przechowywane w plikach zasobów każdego z serwerów. Takie działania mogą wypełniać definicję profilowania w rozumieniu RODO (art. 4 pkt 4). Statystyki służą wyłącznie celom informacyjnym i raportowym — nie są wykorzystywane do podejmowania decyzji w sposób w pełni zautomatyzowany, o skutkach prawnych lub podobnych, w rozumieniu art. 22 RODO.  
`§9.3.` Dane mogą być przetwarzane w infrastrukturze dostawcy usług Discord Inc. z siedzibą w USA, zgodnie z [polityką prywatności Discorda](https://discord.com/privacy).

## §10. Kontakt
`§10.1.` W sprawach związanych z prywatnością i ochroną danych osobowych można kontaktować się przez adres: kontakt@kacpergorka.com.

---

Niniejsza Polityka obowiązuje od dnia 28 września 2025 r.