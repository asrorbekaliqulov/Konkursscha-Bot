// Telegram Bot Configuration
const TELEGRAM_CONFIG = {
  botToken: "8108945501:AAF9bnymPoj7UDE2f3nGNgZUIoQEH2G9poo", // @BotFather dan olingan token
  chatId: "6194484795", // Admin chat ID
}

// Contact Form Handler
document.addEventListener("DOMContentLoaded", () => {
  const contactForm = document.getElementById("contactForm")
  const formMessage = document.getElementById("formMessage")
  const charityBtn = document.getElementById("charityBtn")
  const charityModal = document.getElementById("charityModal")
  const closeModal = document.getElementById("closeModal")

  // Enhanced Form validation
  function validateForm(formData) {
    const errors = {}
    const successes = {}

    // Name validation
    if (!formData.name.trim()) {
      errors.name = "Ism kiritish majburiy"
    } else if (formData.name.trim().length < 2) {
      errors.name = "Ism kamida 2 ta belgidan iborat bo'lishi kerak"
    } else if (formData.name.trim().length > 50) {
      errors.name = "Ism 50 ta belgidan oshmasligi kerak"
    } else if (!/^[a-zA-ZА-Яа-яЁёўғҳқ\s]+$/.test(formData.name.trim())) {
      errors.name = "Ismda faqat harflar bo'lishi kerak"
    } else {
      successes.name = "✓ To'g'ri"
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!formData.email.trim()) {
      errors.email = "Email kiritish majburiy"
    } else if (!emailRegex.test(formData.email)) {
      errors.email = "Email formati noto'g'ri (example@domain.com)"
    } else if (formData.email.length > 100) {
      errors.email = "Email 100 ta belgidan oshmasligi kerak"
    } else {
      successes.email = "✓ To'g'ri"
    }

    // Telegram validation
    const telegramRegex = /^@[a-zA-Z0-9_]{5,32}$/
    if (!formData.telegram.trim()) {
      errors.telegram = "Telegram username kiritish majburiy"
    } else if (!telegramRegex.test(formData.telegram)) {
      errors.telegram = "Format: @username (5-32 ta belgi, faqat harf, raqam, _)"
    } else {
      successes.telegram = "✓ To'g'ri"
    }

    // Message validation
    if (!formData.message.trim()) {
      errors.message = "Xabar kiritish majburiy"
    } else if (formData.message.trim().length < 10) {
      errors.message = "Xabar kamida 10 ta belgidan iborat bo'lishi kerak"
    } else if (formData.message.trim().length > 1000) {
      errors.message = "Xabar 1000 ta belgidan oshmasligi kerak"
    } else {
      successes.message = "✓ To'g'ri"
    }

    return { errors, successes }
  }

  // Show form feedback
  function showFormFeedback(errors, successes) {
    // Clear previous states
    document.querySelectorAll(".form-group").forEach((group) => {
      group.classList.remove("error", "success")
    })
    document.querySelectorAll(".form-error, .form-success").forEach((el) => {
      el.classList.remove("show")
      el.textContent = ""
    })

    // Show errors
    Object.keys(errors).forEach((field) => {
      const group = document.getElementById(field).closest(".form-group")
      const errorElement = document.getElementById(field + "Error")

      if (group && errorElement) {
        group.classList.add("error")
        errorElement.textContent = errors[field]
        errorElement.classList.add("show")
      }
    })

    // Show successes
    Object.keys(successes).forEach((field) => {
      const group = document.getElementById(field).closest(".form-group")
      let successElement = document.getElementById(field + "Success")

      if (group) {
        group.classList.add("success")

        // Create success element if it doesn't exist
        if (!successElement) {
          successElement = document.createElement("span")
          successElement.id = field + "Success"
          successElement.className = "form-success"
          group.appendChild(successElement)
        }

        successElement.textContent = successes[field]
        successElement.classList.add("show")
      }
    })
  }

  // Character counter for message field
  function setupCharacterCounter() {
    const messageField = document.getElementById("message")
    const maxLength = 1000

    // Create counter element
    const counter = document.createElement("span")
    counter.className = "char-counter"
    counter.id = "messageCounter"
    messageField.closest(".form-group").appendChild(counter)

    function updateCounter() {
      const currentLength = messageField.value.length
      const remaining = maxLength - currentLength

      counter.textContent = `${currentLength}/${maxLength}`

      // Update counter color based on remaining characters
      counter.classList.remove("warning", "error")
      if (remaining < 100) {
        counter.classList.add("warning")
      }
      if (remaining < 0) {
        counter.classList.add("error")
      }
    }

    messageField.addEventListener("input", updateCounter)
    updateCounter() // Initial call
  }

  // Show form message
  function showMessage(message, type) {
    formMessage.textContent = message
    formMessage.className = `form-message show ${type}`

    setTimeout(() => {
      formMessage.classList.remove("show")
    }, 7000)
  }

  // Send to Telegram
  async function sendToTelegram(formData) {
    const message = `
🔔 <b>Yangi xabar portfolio saytidan!</b>

👤 <b>Ism:</b> ${formData.name}
📧 <b>Email:</b> ${formData.email}
📱 <b>Telegram:</b> ${formData.telegram}

💬 <b>Xabar:</b>
${formData.message}

📊 <b>Statistika:</b>
• Xabar uzunligi: ${formData.message.length} belgi
• Yuborilgan vaqt: ${new Date().toLocaleString("uz-UZ")}
• IP manzil: ${await getUserIP()}
        `.trim()

    const telegramUrl = `https://api.telegram.org/bot${TELEGRAM_CONFIG.botToken}/sendMessage`

    try {
      const response = await fetch(telegramUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          chat_id: TELEGRAM_CONFIG.chatId,
          text: message,
          parse_mode: "HTML",
        }),
      })

      const result = await response.json()

      if (result.ok) {
        return { success: true }
      } else {
        throw new Error(result.description || "Telegram API xatosi")
      }
    } catch (error) {
      console.error("Telegram yuborishda xato:", error)
      return { success: false, error: error.message }
    }
  }

  // Get user IP (optional)
  async function getUserIP() {
    try {
      const response = await fetch("https://api.ipify.org?format=json")
      const data = await response.json()
      return data.ip
    } catch {
      return "Noma'lum"
    }
  }

  // Modal functions
  function openModal() {
    charityModal.classList.add("show")
    document.body.style.overflow = "hidden"

    // Send notification to Telegram
    const charityMessage = `
🎯 <b>Xayriya so'rovi</b>

Kimdir sizning loyihalaringizni qo'llab-quvvatlashni xohlaydi!

⏰ <b>Vaqt:</b> ${new Date().toLocaleString("uz-UZ")}
    `.trim()

    fetch(`https://api.telegram.org/bot${TELEGRAM_CONFIG.botToken}/sendMessage`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: TELEGRAM_CONFIG.chatId,
        text: charityMessage,
        parse_mode: "HTML",
      }),
    }).catch(console.error)
  }

  function closeModalFunc() {
    charityModal.classList.remove("show")
    document.body.style.overflow = "auto"
  }

  // Form submit handler
  contactForm.addEventListener("submit", async (e) => {
    e.preventDefault()

    const submitBtn = contactForm.querySelector(".form-submit")
    const formData = {
      name: document.getElementById("name").value,
      email: document.getElementById("email").value,
      telegram: document.getElementById("telegram").value,
      message: document.getElementById("message").value,
    }

    // Validate form
    const { errors, successes } = validateForm(formData)
    showFormFeedback(errors, successes)

    if (Object.keys(errors).length > 0) {
      showMessage("❌ Iltimos, barcha xatolarni to'g'rilang", "error")
      return
    }

    // Show loading state
    submitBtn.classList.add("loading")
    submitBtn.disabled = true

    try {
      // Send to Telegram
      const result = await sendToTelegram(formData)

      if (result.success) {
        showMessage("✅ Xabaringiz muvaffaqiyatli yuborildi! 24 soat ichida javob beramiz.", "success")
        contactForm.reset()

        // Clear all feedback
        document.querySelectorAll(".form-group").forEach((group) => {
          group.classList.remove("error", "success")
        })
        document.querySelectorAll(".form-error, .form-success").forEach((el) => {
          el.classList.remove("show")
        })

        // Reset character counter
        const counter = document.getElementById("messageCounter")
        if (counter) counter.textContent = "0/1000"
      } else {
        showMessage("❌ Xabar yuborishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.", "error")
      }
    } catch (error) {
      console.error("Form yuborishda xato:", error)
      showMessage("❌ Texnik xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.", "error")
    } finally {
      // Hide loading state
      submitBtn.classList.remove("loading")
      submitBtn.disabled = false
    }
  })

  // Real-time validation
  const inputs = contactForm.querySelectorAll("input, textarea")
  inputs.forEach((input) => {
    input.addEventListener("input", function () {
      const formData = {
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        telegram: document.getElementById("telegram").value,
        message: document.getElementById("message").value,
      }

      const { errors, successes } = validateForm(formData)

      // Only show feedback for current field
      const currentField = this.id
      const group = this.closest(".form-group")
      const errorElement = document.getElementById(currentField + "Error")
      let successElement = document.getElementById(currentField + "Success")

      // Clear current field state
      group.classList.remove("error", "success")
      if (errorElement) errorElement.classList.remove("show")
      if (successElement) successElement.classList.remove("show")

      if (errors[currentField]) {
        group.classList.add("error")
        if (errorElement) {
          errorElement.textContent = errors[currentField]
          errorElement.classList.add("show")
        }
      } else if (successes[currentField] && this.value.trim()) {
        group.classList.add("success")

        if (!successElement) {
          successElement = document.createElement("span")
          successElement.id = currentField + "Success"
          successElement.className = "form-success"
          group.appendChild(successElement)
        }

        successElement.textContent = successes[currentField]
        successElement.classList.add("show")
      }
    })
  })

  // Event listeners
  charityBtn.addEventListener("click", (e) => {
    e.preventDefault()
    openModal()
  })

  closeModal.addEventListener("click", closeModalFunc)

  // Close modal when clicking outside
  charityModal.addEventListener("click", (e) => {
    if (e.target === charityModal) {
      closeModalFunc()
    }
  })

  // Close modal with Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && charityModal.classList.contains("show")) {
      closeModalFunc()
    }
  })

  // Initialize character counter
  setupCharacterCounter()
})

// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault()
    const target = document.querySelector(this.getAttribute("href"))
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    }
  })
})

// Header background on scroll
window.addEventListener("scroll", () => {
  const header = document.querySelector(".header")
  if (window.scrollY > 100) {
    header.style.background = "rgba(10, 10, 10, 0.98)"
  } else {
    header.style.background = "rgba(10, 10, 10, 0.95)"
  }
})

// Intersection Observer for animations
const observerOptions = {
  threshold: 0.1,
  rootMargin: "0px 0px -50px 0px",
}

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = "1"
      entry.target.style.transform = "translateY(0)"
    }
  })
}, observerOptions)

// Observe elements for animation
document.querySelectorAll(".skill-card, .stat, .contact-item").forEach((el) => {
  el.style.opacity = "0"
  el.style.transform = "translateY(20px)"
  el.style.transition = "opacity 0.6s ease, transform 0.6s ease"
  observer.observe(el)
})

// Typing animation for code block
const codeLines = document.querySelectorAll(".code-line")
let delay = 0

codeLines.forEach((line, index) => {
  line.style.opacity = "0"
  setTimeout(() => {
    line.style.opacity = "1"
    line.style.animation = "typewriter 0.5s ease-in-out"
  }, delay)
  delay += 200
})

// Add typewriter animation keyframes
const style = document.createElement("style")
style.textContent = `
    @keyframes typewriter {
        from {
            width: 0;
            opacity: 0;
        }
        to {
            width: 100%;
            opacity: 1;
        }
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`
document.head.appendChild(style)

// Console easter egg for developers
console.log(`
    ╔══════════════════════════════════════╗
    ║          Backend Developer           ║
    ║                                      ║
    ║  Salom! Kodimni ko'rib chiqyapsizmi? ║
    ║  GitHub: github.com/asrorbekaliqulov ║
    ║  Email: asrorbekaliqulov08@gmail.com ║
    ╚══════════════════════════════════════╝
`)
