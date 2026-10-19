### 1\. ไฟล์ `requirements.txt` (บอกไลบรารีที่ต้องใช้)

สร้างไฟล์ชื่อ **requirements.txt** แล้วใส่โค้ดนี้ลงไป:

```
fastapi
uvicorn
pydantic
pyjwt
httpx

```

---

### 2\. ไฟล์ `README.md` (หน้าอธิบายโปรเจกต์สวยๆ บน GitHub)

สร้างไฟล์ชื่อ **README.md** แล้วใส่เนื้อหานี้ลงไป (เวลากดดูหน้า GitHub จะมีคู่มือสวยงามทันที):

```
# 💰 Daily Expense Tracker API &amp; Web Application

ระบบบันทึกและจัดการรายจ่ายประจำวัน พัฒนาด้วย **Python FastAPI**, **SQLite**, **HTML5**, และ **Tailwind CSS**

## ✨ คุณสมบัติหลัก (Key Features)
* 📝 **CRUD รายจ่าย:** เพิ่ม, ดู, แก้ไข, และลบรายการรายจ่าย
* 🔒 **Authentication &amp; OAuth:** สมัครสมาชิก/เข้าสู่ระบบด้วย JWT Token และรองรับ Google &amp; GitHub OAuth
* 🛡️ **Data Validation:** ตรวจสอบความถูกต้องของข้อมูลด้วย Pydantic (ห้ามเงินติดลบ/คุมฟอร์แมตวันที่)
* 🔍 **Search &amp; Filter:** ค้นหาด้วยคำค้น หมวดหมู่ และกรองตามช่วงวันที่ (ตั้งแต่วันที่ - ถึงวันที่)
* 📊 **Dashboard &amp; Chart:** สรุปยอดเงินรวม รายการทั้งหมด และแสดงกราฟโดนัทด้วย Chart.js

## 🚀 วิธีการติดตั้งและรันโปรเจกต์ (Getting Started)

1. **ติดตั้ง Dependencies:**
   ```bash
   pip install -r requirements.txt

```

1. **สั่งรันเซิร์ฟเวอร์:**

```
uvicorn main:app --reload

```

1. **เข้าใช้งาน:**
  * หน้าเว็บหลัก: `http://localhost:8000`
  * API Documentation (Swagger UI): `http://localhost:8000/docs`

```

---

### 💻 คำสั่ง Push 2 ไฟล์นี้ขึ้น GitHub (รันใน Terminal):

```bash
git add requirements.txt README.md
git commit -m "Add requirements.txt and README.md"
git push origin main
```
