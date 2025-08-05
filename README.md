# Think. Invest. Improve - סימולציית השקעה רטרואקטיבית

אפליקציית Streamlit לניתוח ביצועי תיק השקעות היסטורי עם השוואה ל-benchmarks.

## תכונות

- 📊 **סימולציה רטרואקטיבית**: בדוק איך תיק השקעות היה מתנהג בעבר
- 📈 **השוואת ביצועים**: השווה לביצועי benchmarks שונים (SPY, QQQ, וכו')
- 📉 **מדדי סיכון**: חישוב תנודתיות, Sharpe Ratio, ו-Max Drawdown
- 🎯 **אופטימיזציה אוטומטית**: בדוק 100 שילובים שונים למציאת השילוב הטוב ביותר
- 📋 **ייצוא PDF**: הורד דוח מפורט בפורמט PDF
- 🎯 **תמיכה בקריפטו**: כולל Bitcoin ו-ETFs אחרים

## התקנה

1. התקן את הדרישות:
```bash
pip install -r requirements.txt
```

2. הרץ את האפליקציה:
```bash
streamlit run app.py
```

## שימוש

1. **הגדר תאריכים**: בחר תאריך התחלה וסיום לניתוח
2. **הכנס תיק השקעות**: הוסף מניות ואחוזי השקעה (סה״כ 100%)
3. **בחר Benchmark**: בחר מדד להשוואה
4. **הרץ ניתוח**: לחץ על כפתור "הרץ ניתוח"
5. **הצע שילוב חדש**: לחץ על "הצע שילוב חדש" לקבלת אופטימיזציה
6. **צפה בתוצאות**: גרפים, מדדי ביצוע, והשוואות
7. **ייצא דוח**: הורד דוח PDF מפורט

## דוגמאות Benchmarks

- **SPY**: S&P 500 ETF
- **QQQ**: NASDAQ-100 ETF
- **IWM**: Russell 2000 ETF
- **TLT**: Treasury Bonds ETF
- **GLD**: Gold ETF
- **BTC-USD**: Bitcoin

## מדדי ביצוע

- **תשואה כוללת**: הרווח/הפסד הכולל בתקופה
- **תשואה שנתית**: תנודתיות שנתית
- **Sharpe Ratio**: יחס תשואה לסיכון
- **Max Drawdown**: הירידה המקסימלית מהשיא 