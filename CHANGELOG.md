# Changelog - KSeF XML Generator

Wszystkie istotne zmiany w projekcie, ze szczególnym uwzględnieniem poprawek błędów i dostosowania do struktury FA(3).

## [1.2.0] - 2026-05-22

### Dodano
- **Uniwersalna warstwa dostępu do danych (`_get_val`)**: Klasa `KsefGenerator` potrafi teraz obsługiwać dane wejściowe w formacie słowników (`dict`), obiektów `pyodbc.Row` oraz krotek (`tuple`). Rozwiązuje to problem "row indices must be integers".
- **Heurystyka usług transportowych**: Automatyczne rozpoznawanie pozycji "transport" i "shipping" jako usług eksportowych (OO), nawet jeśli w bazie są oznaczone jako towary.
- **Logowanie i debugowanie**: Rozszerzone komunikaty w `main.py` informujące o każdym etapie pobierania danych z bazy.

### Zmieniono
- **Zgodność z FA(3)**: 
    - Przeniesiono Odwrotne Obciążenie (OO) i Eksport Usług z pola `P_13_6_2` (WDT) do poprawnego pola **`P_13_5`**.
    - Zmieniono adnotację odwrotnego obciążenia z `P_18` na **`P_18A`**.
    - Ustawiono wymaganą stawkę **`oo`** w polu `P_12` dla wierszy z odwrotnym obciążeniem.
- **Restrykcyjna separacja kursów**:
    - **Obliczenia**: Używają wyłącznie kursu z bazy (`dok_WalutaKurs`), co eliminuje błędy zaokrągleń (np. powrót z PLN do równego 470.00 EUR).
    - **Informacja**: Tag `<KursWaluty>` używa wyłącznie aktualnego kursu z API NBP.
- **Kolejność pól w XML**: Identyfikatory (NIP/KodUE) są teraz zawsze generowane przed nazwą firmy, zgodnie z wymogami schemy XSD FA(3).

### Naprawiono
- Błąd `row indices must be integers, not str` występujący przy wywołaniach webowych (Flask/Debugger).
- Błędne klasyfikowanie usług wewnątrzunijnych jako WDT (teraz trafiają do NP/OO).
- Błąd zaokrągleń walutowych przy przeliczaniu kwot netto z bazy.

## [1.1.0] - 2026-05-19

### Dodano
- Obsługa stawek zwolnionych (`zw`) i niepodlegających (`np`).
- Automatyczne pobieranie kursów walut z NBP na podstawie daty wystawienia faktury.
- Obsługa wielu stawek VAT na jednej fakturze.

## [1.0.0] - Pierwsza wersja stabilna

### Dodano
- Wyciąganie danych z Subiekt GT via pyodbc.
- Podstawowy generator XML zgodny z FA(2).
- Konfiguracja serwera bazy danych przez `.env`.
