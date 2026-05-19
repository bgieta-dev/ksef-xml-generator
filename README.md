# Subiekt GT -> KSeF XML Generator

Prosty skrypt do wyciągania danych z bazy Subiekta GT (MSSQL) i generowania plików XML zgodnych ze strukturą FA(3) dla KSeF.

## Jak to ugryźć?

1. **Wymagania**: Musisz mieć zainstalowane `pyodbc` (do bazy) i `python-dotenv` (do konfiguracji). Wszystko jest w `requirements.txt`.
2. **Konfiguracja**:
   - Skopiuj plik `.env.example` i zmień mu nazwę na `.env`.
   - Wpisz tam dane do swojej bazy (IP serwera, nazwa bazy, użytkownik SQL).
3. **Uruchomienie**:
   - Żeby zobaczyć ostatnie 10 faktur i sprawdzić czy połączenie działa, odpal: `python list_invoices.py`.
   - Żeby wygenerować XML dla najnowszej faktury, odpal: `python main.py`.

## Logika generowania XML FA(3)

Od wersji 2026-05-19 generator obsługuje strukturę **FA(3)**. Poniżej kluczowe zasady mapowania dla różnych rodzajów faktur:

### 1. Rodzaje transakcji i mapowanie VAT
- **Krajowa (Standard)**:
  - Stawki 23%, 8%, 5% są mapowane do odpowiednich sekcji `P_13_x` (netto) i `P_14_x` (VAT).
  - `P_12` w pozycjach przyjmuje wartość liczbową (np. "23").
- **WDT (Wewnątrzwspólnotowa Dostawa Towarów) i Eksport**:
  - Wykrywane na podstawie stawki 0% w Subiekcie.
  - Wartości trafiają do pola `P_13_5`.
  - `P_12` w pozycjach ustawiane na "0".
- **Odwrotne Obciążenie (OO / Reverse Charge)**:
  - Wykrywane, gdy pozycja nie ma przypisanej stawki VAT (null w bazie).
  - **Kluczowa adnotacja**: Pole `P_18` w sekcji `Adnotacje` musi mieć wartość **1**.
  - Wartości netto trafiają do pola `P_13_7`.
  - `P_12` w pozycjach ustawiane na "np".

### 2. Wymogi Techniczne FA(3)
- **UU_ID**: Każdy wiersz faktury (`FaWiersz`) posiada unikalny 16-znakowy identyfikator w tagu `UU_ID`.
- **RodzajFaktury**: Obowiązkowy tag, obecnie ustawiony na `VAT`.
- **Adnotacje**: Zmieniona struktura względem FA(2). Pola `P_19`, `P_22`, `P_PMarzy` są teraz elementami strukturalnymi (np. `<Zwolnienie><P_19N>1</P_19N></Zwolnienie>`).
- **P_1 (Data)**: Zawsze używana jest data wystawienia z dokumentu źródłowego (nie data generowania).

### 3. Waluty i kursy
- Jeśli waluta != PLN, generator automatycznie pobiera kurs NBP z dnia roboczego poprzedzającego datę sprzedaży/wystawienia.
- W pozycjach dodawany jest tag `KursWaluty` (informacyjnie).
- Kwoty VAT w sekcjach `P_14_xW` są przeliczane na PLN wg kursu z dokumentu.
