window.SWIPIES_OPERATIONS_I18N = {
  "ru": {
    "menuOpen": "Открыть меню",
    "menuClose": "Закрыть меню",
    "scenarios": [
      {
        "icon": "workflow",
        "title": "Проверка остатков на складах",
        "preview": "Мгновенный запрос к 1С и ERP по артикулам и филиалам",
        "dialog": [
          {
            "role": "user",
            "sender": "Менеджер",
            "text": "Проверь наличие по артикулу ART-8842 на складах Ташкент и Самарканд."
          },
          {
            "role": "bot",
            "sender": "Ops-агент",
            "text": "Запрос к ERP выполнен:\n• Склад Ташкент: 34 шт. (свободно к отгрузке)\n• Склад Самарканд: 12 шт. (в резерве 4 шт., доступно 8 шт.)\nПоставить товар в резерв для клиента?"
          },
          {
            "role": "user",
            "sender": "Менеджер",
            "text": "Зарезервируй 10 шт. в Ташкенте для ООО «Восток»."
          },
          {
            "role": "bot",
            "sender": "Ops-агент",
            "text": "Резерв #RZ-2041 успешно создан в 1C. Срок брони — 3 рабочих дня. Ссылка на карточку заказа отправлена в CRM."
          }
        ]
      },
      {
        "icon": "clock",
        "title": "Статус заказа и отгрузка",
        "preview": "Быстрый трекинг доставки и уведомление клиента",
        "dialog": [
          {
            "role": "user",
            "sender": "Клиент",
            "text": "Подскажите, где находится заказ #ORD-9201 и когда ожидается доставка?"
          },
          {
            "role": "bot",
            "sender": "Ops-агент",
            "text": "Заказ #ORD-9201 собран и передан курьеру сегодня в 08:30. Статус: «В пути». Ожидаемое время доставки: сегодня до 16:00. Контакт курьера: +998 (90) 123-45-67."
          },
          {
            "role": "user",
            "sender": "Клиент",
            "text": "Можно перенести доставку на офис по ул. Амира Темура, 45?"
          },
          {
            "role": "bot",
            "sender": "Ops-агент",
            "text": "Адрес успешно обновлён в логистической системе и передан курьеру. Смс с подтверждением отправлено."
          }
        ]
      },
      {
        "icon": "clipboard-list",
        "title": "Обновление сделки в CRM",
        "preview": "Смена этапа воронки и генерация счёта из переписки",
        "dialog": [
          {
            "role": "user",
            "sender": "Менеджер",
            "text": "Клиент согласовал спецификацию по сделке #512. Переведи на этап «Счёт выставлен» и сформируй счёт."
          },
          {
            "role": "bot",
            "sender": "Ops-агент",
            "text": "Сделка #512 (ООО «ПромТех») переведена на этап «Счёт выставлен» в AmoCRM. Сгенерирован счёт #INV-109 на сумму 18 500 000 сум с НДС. PDF-файл прикреплен к сделке."
          },
          {
            "role": "user",
            "sender": "Менеджер",
            "text": "Отправь ссылку на счёт клиенту в Telegram."
          },
          {
            "role": "bot",
            "sender": "Ops-агент",
            "text": "Счёт отправлен контактному лицу в Telegram. В сделке зафиксировано время отправки."
          }
        ]
      }
    ]
  },
  "uz": {
    "menuOpen": "Menyuni ochish",
    "menuClose": "Menyuni yopish",
    "scenarios": [
      {
        "icon": "workflow",
        "title": "Ombor qoldiqlarini tekshirish",
        "preview": "Artikullar va filiallar bo‘yicha 1C va ERP ga tezkor so‘rov",
        "dialog": [
          {
            "role": "user",
            "sender": "Menejer",
            "text": "Toshkent va Samarqand omborlarida ART-8842 artikuli bo‘yicha qoldiqni tekshir."
          },
          {
            "role": "bot",
            "sender": "Ops-agent",
            "text": "ERP tizimiga so‘rov bajarildi:\n• Toshkent ombori: 34 dona (jo‘natishga tayyor)\n• Samarqand ombori: 12 dona (4 dona band, 8 dona mavjud)\nMijoz uchun band qilib qo‘yaymi?"
          },
          {
            "role": "user",
            "sender": "Menejer",
            "text": "Toshkentdan «Vostok» MChJ uchun 10 dona band qil."
          },
          {
            "role": "bot",
            "sender": "Ops-agent",
            "text": "1C da #RZ-2041 raqamli band qilish hujjati yaratildi. Bandlik muddati — 3 ish kuni. Havola CRM ga uzatildi."
          }
        ]
      },
      {
        "icon": "clock",
        "title": "Buyurtma holati va yetkazish",
        "preview": "Tezkor yetkazish monitoringi va mijozni xabardor qilish",
        "dialog": [
          {
            "role": "user",
            "sender": "Mijoz",
            "text": "#ORD-9201 raqamli buyurtmam qayerda va qachon yetkaziladi?"
          },
          {
            "role": "bot",
            "sender": "Ops-agent",
            "text": "#ORD-9201 buyurtmasi yig‘ildi va bugun 08:30 da kuryerga topshirildi. Holati: «Yo‘lda». Yetkazish vaqti: bugun soat 16:00 gacha. Kuryer telefoni: +998 (90) 123-45-67."
          },
          {
            "role": "user",
            "sender": "Mijoz",
            "text": "Yetkazish manzilini Amir Temur ko‘chasi, 45-uyga o‘zgartirsa bo‘ladimi?"
          },
          {
            "role": "bot",
            "sender": "Ops-agent",
            "text": "Manzil logistika tizimida yangilandi va kuryerga yetkazildi. Tasdiqlash SMS xabari yuborildi."
          }
        ]
      },
      {
        "icon": "clipboard-list",
        "title": "CRM dagi bitimni yangilash",
        "preview": "Bosqichni o‘zgartirish va yozishmadan hisob shakllantirish",
        "dialog": [
          {
            "role": "user",
            "sender": "Menejer",
            "text": "Mijoz #512 bitim bo‘yicha shartlarni tasdiqladi. «Hisob chiqarildi» bosqichiga o‘tkaz va hisob tuz."
          },
          {
            "role": "bot",
            "sender": "Ops-agent",
            "text": "AmoCRM da #512 bitimi «Hisob chiqarildi» bosqichiga o‘tkazildi. QQS bilan 18 500 000 so‘mlik #INV-109 hisob shakllantirildi va PDF bitimga biriktirildi."
          },
          {
            "role": "user",
            "sender": "Menejer",
            "text": "Hisob havolasini mijozga Telegram orqali yubor."
          },
          {
            "role": "bot",
            "sender": "Ops-agent",
            "text": "Hisob mijozning Telegram raqamiga yuborildi. CRM da yuborilgan vaqt qayd etildi."
          }
        ]
      }
    ]
  },
  "en": {
    "menuOpen": "Open menu",
    "menuClose": "Close menu",
    "scenarios": [
      {
        "icon": "workflow",
        "title": "Warehouse Stock Availability",
        "preview": "Real-time multi-branch inventory lookup via ERP API",
        "dialog": [
          {
            "role": "user",
            "sender": "Manager",
            "text": "Check stock for SKU ART-8842 across Tashkent and Samarkand warehouses."
          },
          {
            "role": "bot",
            "sender": "Ops Agent",
            "text": "ERP lookup completed:\n• Tashkent Warehouse: 34 units (ready to ship)\n• Samarkand Warehouse: 12 units (4 reserved, 8 available)\nShall I place a hold for a customer?"
          },
          {
            "role": "user",
            "sender": "Manager",
            "text": "Reserve 10 units at Tashkent for Vostok LLC."
          },
          {
            "role": "bot",
            "sender": "Ops Agent",
            "text": "Reservation #RZ-2041 created in ERP. Reservation valid for 3 business days. Deal card link updated in CRM."
          }
        ]
      },
      {
        "icon": "clock",
        "title": "Order Status & Tracking",
        "preview": "Instant dispatch tracking and automated customer notification",
        "dialog": [
          {
            "role": "user",
            "sender": "Client",
            "text": "Can you provide an update on order #ORD-9201 delivery timing?"
          },
          {
            "role": "bot",
            "sender": "Ops Agent",
            "text": "Order #ORD-9201 was packaged and handed to courier today at 08:30. Status: \"Out for delivery\". Expected delivery: today before 16:00. Courier phone: +998 (90) 123-45-67."
          },
          {
            "role": "user",
            "sender": "Client",
            "text": "Can we redirect delivery to our branch office at 45 Amir Temur Ave?"
          },
          {
            "role": "bot",
            "sender": "Ops Agent",
            "text": "Delivery address updated in the dispatch system and notified to the courier. Confirmation SMS dispatched."
          }
        ]
      },
      {
        "icon": "clipboard-list",
        "title": "Automated CRM Deal Sync",
        "preview": "Stage progression and invoice generation straight from chats",
        "dialog": [
          {
            "role": "user",
            "sender": "Sales Rep",
            "text": "Client approved specification on deal #512. Move to \"Invoice Sent\" and generate PDF invoice."
          },
          {
            "role": "bot",
            "sender": "Ops Agent",
            "text": "Deal #512 (TechProm LLC) progressed to \"Invoice Sent\" in CRM. Generated invoice #INV-109 for 18,500,000 UZS incl. VAT. PDF copy attached to CRM deal."
          },
          {
            "role": "user",
            "sender": "Sales Rep",
            "text": "Send the invoice link to the client via Telegram."
          },
          {
            "role": "bot",
            "sender": "Ops Agent",
            "text": "Invoice delivered to the customer via Telegram. Timestamp logged on the deal timeline."
          }
        ]
      }
    ]
  }
};
