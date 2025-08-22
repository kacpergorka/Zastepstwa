# Aktualizacje zastępstw wysyłane na platformie Discord
> Kod bota przystosowany jest do zastępstw [Zespołu Szkół Elektronicznych w Bydgoszczy](https://zastepstwa.zse.bydgoszcz.pl/). Jesteś uczniem tej szkoły? [Dodaj bota](https://discord.com/oauth2/authorize?client_id=1278769348822962196&permissions=8&integration_type=0&scope=bot+applications.commands), a następnie ciesz się z nieomijających Ciebie zastępstw. Wszystkie ważne informacje znajdziesz w wiadomości prywatnej wysłanej przez bota.

# Informacje techniczne
Bot na platformie Discord udostępnia aktualizacje zastępstw, które pobiera ze strony internetowej korzystającej z usługi [Zastępstwa Optivum firmy VULCAN](https://duckduckgo.com/?t=h_&q=Zast%C4%99pstwa+Optivum+firmy+VULCAN&ia=web).

W przypadku wystąpienia jakiegokolwiek błędu z zakresu poprawnego funkcjonowania bota lub prawidłowego wysyłania zastępstw, utwórz issue z dokładnym opisem błędu, a w miarę możliwości postaram się odpowiednio szybko go naprawić. Aby skontaktować się z administratorami bota, użyj polecenia `/informacje` i postępuj zgodnie z instrukcjami.

Jeżeli jesteś uczniem innej szkoły, która tak samo, jak [Zespół Szkół Elektronicznych w Bydgoszczy](https://zse.bydgoszcz.pl/) korzysta z usługi [Zastępstwa Optivum firmy VULCAN](https://duckduckgo.com/?t=h_&q=Zast%C4%99pstwa+Optivum+firmy+VULCAN&ia=web) i chciałbyś, aby twoja szkoła dostała wsparcie przez bota, skontaktuj się ze mną, a w miarę możliwości postaram się wdrożyć Twoją szkołę do procesu konfiguracji.

# Największe atrybuty bota
### Wybór kanału do wysyłania zastępstw
Bot umożliwia wybranie dedykowanego kanału tekstowego, na który będą wysyłane zastępstwa, przy pomocy polecenia `/skonfiguruj`. Dzięki temu wszystkie istotne informacje trafią do wybranej grupy użytkowników.

![](https://github.com/user-attachments/assets/22cc4a0d-a540-4732-920a-f8cf848c6526)

### Filtracja zastępstw przystosowana dla uczniów i nauczycieli
Jedną z najważniejszych funkcji bota jest konfigurowana filtracja zastępstw, w dalszym procesie polecenia `/skonfiguruj`. Podczas konfiguracji możesz wskazać, które klasy lub którzy nauczyciele Cię interesują. Efekt? Otrzymujesz jedynie powiadomienia, które naprawdę Cię dotyczą, bez konieczności przeglądania całej listy zastępstw. Jeżeli wprowadzisz nazwę klasy lub nazwisko z błędem, bot zaproponuje najbardziej prawdopodobne poprawne dopasowania.

![](https://github.com/user-attachments/assets/e88894e4-5ef1-434a-871b-19dc581a6284)

### Zaawansowane wyszukiwanie i filtrowanie zastępstw
Bot potrafi inteligentnie dopasować wpisy zastępstw nawet wtedy, gdy nazwy klas czy nazwiska nauczycieli zapisane są w różny sposób. Wyodrębniając znaki specjalne, kropki, polskie znaki diakrytyczne czy zbędne spacje, a także rozpoznając skróty oraz inicjały bezbłędnie wyselekcjonowuje zastępstwa dla zastosowanej filtracji.

![](https://github.com/user-attachments/assets/44c43199-d928-4784-afeb-e2efa80cf929)

### Statystyki zastępstw
Za pomocą polecenia `/statystyki` jesteś w stanie zobaczyć jaką ilość zastępstw bot dostarczył na Twój serwer oraz listę nauczycieli z największą liczbą odnotowanych zastępstw. Na zakończenie roku szkolnego bot automatycznie wyśle podsumowanie całorocznego dostarczania zastępstw na serwer, a Ty będziesz w stanie zobaczyć, którzy nauczyciele najczęściej zostawali odnotowywani.

![](https://github.com/user-attachments/assets/1cb6ed7a-063d-4e93-9b70-157496ffb34c)

### Czytelny i przejrzysty interfejs
Dzięki wykorzystaniu nowoczesnych elementów interfejsu, udostępnionych przez Discorda, bot oferuje intuicyjny sposób konfiguracji oraz przejrzyście i czytelnie sformatowane zastępstwa.

![](https://github.com/user-attachments/assets/a4248095-d4c9-4ebc-9463-13355aef1caa)

# Instalacja oprogramowania
	git clone https://github.com/kacpergorka/zastepstwa/
	cd .\zastepstwa\
	pip install -r requirements.txt

Po sklonowaniu repozytorium i zainstalowaniu wymaganych bibliotek uruchom plik `main.py` i poczekaj, aż wygeneruje się domyślny plik `config.json`. Następnie uzupełnij wygenerowany plik, według [przykładowego pliku konfiguracyjnego](https://github.com/user-attachments/files/21945674/config.json).

#
Projekt licencjonowany na podstawie [Licencji MIT](./LICENSE). Stworzone z ❤️ przez Kacpra Górkę!