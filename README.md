# Subiekt GT -> KSeF XML Generator (FA(3))

Lekki skrypt ETL do generowania e-Faktur. 

## 🛠 Szybki Start
1. `.env`: `DB_SERVER`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
2. Uruchom: `python main.py` (pobiera najnowszą FS z bazy).

---

## 🧠 Kompendium Wiedzy (Dla Dewelopera / Serwisu)

### 1. Źródła Danych (MSSQL - Subiekt GT)
*   **Nagłówek**: `dok__Dokument`. Kluczowe pola: `dok_WalutaKurs`, `dok_WartNettoWal`.
*   **Pozycje**: `dok_Pozycja`. Uwaga: W Subiekcie pozycje są **zawsze w PLN**.
*   **Kartoteki**: `tw__Towar`. Pole `tw_Rodzaj`: 1=Towar, 2=Usługa.
*   **VAT**: `sl_StawkaVAT`. Pole `vat_Symbol`: "np", "zw", "23" itd.

### 2. Logika Biznesowa (Gdzie szukać przyczyn?)
*   **Problem z kwotami?** -> `ksef_generator.py`. Szukaj `kurs_dok`. Kwoty walutowe są REKONSTRUOWANE przez `PLN / kurs_dok`. Jeśli w XML jest np. 470.23 zamiast 470.00, sprawdź czy do obliczeń nie został użyty `kurs_nbp`.
*   **Błędny koszyk VAT (np. WDT zamiast OO)?** -> Sprawdź metodę `generate()`. Klasyfikacja zależy od: `tw_Rodzaj`, `vat_Symbol`, kraju nabywcy i heurystyki nazw (słowa "transport"/"shipping" wymuszają OO).
*   **Błąd "indices must be integers"?** -> To błąd typów `pyodbc.Row` vs `dict`. Rozwiązanie to metoda `_get_val()` w generatorze – używaj jej zawsze do pobierania jakiejkolwiek wartości.

### 3. Mapa Koszyków FA(3)
| Typ Transakcji | Pole XML | Adnotacja P_18A | Stawka P_12 |
| :--- | :--- | :--- | :--- |
| Eksport Usług / OO / NP | `P_13_5` | **1** | `oo` |
| WDT | `P_13_6_2` | 2 | `0 WDT` |
| Eksport Towarów | `P_13_6_3` | 2 | `0 EX` |
| Krajowa 0% | `P_13_4` | 2 | `0` |
| Zwolnione | `P_13_7` | 2 | `zw` |

### 4. Obsługa Walut (Krytyczne!)
*   **Obliczenia**: Tylko kurs z bazy (`dok_WalutaKurs`).
*   **Tag <KursWaluty>**: Tylko kurs z API NBP (wyłącznie informacja).
*   **VAT w PLN**: Pole `P_14_xW` musi zawierać wartość z bazy Subiekta (`ob_WartVat`).

### 5. Rozwiązywanie Problemów (FAQ)
*   **Błąd 500 w przeglądarce?** -> Sprawdź logi Flask/serwera. Prawdopodobnie brak `pyodbc` w środowisku serwera lub brak dostępu do `.env`.
*   **Brak połączenia?** -> Sprawdź `config.py`. Wymagany `ODBC Driver 18`. Jeśli serwer nie ma SSL, flagi `Encrypt=no;TrustServerCertificate=yes` są obowiązkowe.
*   **Niewłaściwa nazwa firmy?** -> KSeF wymaga najpierw NIP, potem Nazwy. Kod dba o tę kolejność.

---
*Ostatnia stabilna wersja: 2026-05-22. Autor: Gemini CLI.*
