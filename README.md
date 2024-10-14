# Aktualizacja zastępstw wysyłana na platformie Discord
> Kod bota przystosowany jest do zastępstw [Zespołu Szkół Elektronicznych w Bydgoszczy](https://zastepstwa.zse.bydgoszcz.pl/). Jesteś uczniem tej szkoły? [Dodaj bota](https://discord.com/oauth2/authorize?client_id=1278769348822962196&permissions=8&integration_type=0&scope=applications.commands+bot), a następnie skontaktuj się z jego administratorami. Wszystkie ważne informacje znajdziesz, używając komendy `/informacje`.

# Informacje techniczne
Bot na platformie Discord udostępnia aktualizacje zastępstw, które pobiera ze strony internetowej korzystającej z usługi [Zastępstwa Optivum firmy VULCAN](https://duckduckgo.com/?t=h_&q=Zast%C4%99pstwa+Optivum+firmy+VULCAN&ia=web).

Kod bota został przystosowany dla mniej doświadczonych programistów, którzy chcą go wykorzystać. Wszystkie zmienne na początku kodu utworzone z myślą o łatwej możliwości wprowadzania zmian posiadają dołączony komentarz z dokładnym opisem ich funkcji. Jeżeli wystąpią jakiekolwiek błędy z zakresu poprawnego wysyłania zastępstw, również innych szkół, utwórz issue z dokładnym opisem błędu oraz jeżeli błąd dotyczy innej szkoły, to dołącz link do strony, z której bot pobiera zastępstwa, a postaram się odpowiednio naprawić owe błędy. Wszystkie niezbędne do prawidłowego działania kodu zewnętrzne biblioteki znajdują się w pliku `requirements.txt`. Po pobraniu plików z repozytorium GitHuba pierwszą rzeczą, jaką powinieneś zrobić przed uruchomieniem bota, jest zmienienie nazwy pliku `config-pattern.json` na `config.json`, a następnie w tym samym pliku wprowadzenie tokenu bota do `"token"` oraz dodanie ID swojego konta Discord do `"allowed_users"`. Ustawienie dozwolonych serwerów oraz dalsza konfiguracja jest przeznaczona komendom.

# Najważniejsze funkcje bota
### Wybór kanału wysyłanych zastępstw
Bot umożliwia administratorom serwera ustawienie dedykowanego kanału tekstowego, na który będą wysyłane zastępstwa, przy pomocy komendy `/skonfiguruj`. Dzięki temu wszystkie istotne informacje trafią do wybranej grupy użytkowników.

### Filtracja zastępstw po klasach
Administratorzy serwera mogą skonfigurować filtrowanie zastępstw, również przy użyciu tej samej komendy `/skonfiguruj`. Pozwala to na wysyłanie aktualizacji tylko dla wybranych klas, co pomaga w znalezieniu swoich zastępstw.

### Bezpieczeństwo
Bot, który znajduję się na serwerze, nie będzie działał bez uprzedniego dodania ID serwera do pliku konfiguracyjnego bota. Taką czynność mogą dokonać osoby, których ID zostało wcześniej umieszczone własnoręcznie w pliku konfiguracyjnym bota przez administratora kodu, za pomocą komendy `/zarządzaj`. Takie działanie ma zapobiec nieautoryzowanym wykorzystaniem bota bez świadomości jego administratora.

### Przyjazny interfejs
Dzięki wykorzystaniu elementów interfejsu udostępnionych przez Discorda takich jak selektory czy przyciski, bot oferuje intuicyjny sposób konfiguracji oraz przejrzyście i czytelnie sformatowane zastępstwa, które umieszcza na wskazanym wcześniej kanale.

#
Ten projekt jest licencjonowany na podstawie [Licencji MIT](./LICENSE).
