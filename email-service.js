// Email proxy service (frontend -> Flask backend -> SendGrid)
// Configure SENDGRID_API_KEY and SENDGRID_FROM_EMAIL on backend (.env)

function getEmailApiUrl() {
    const host = window.location.hostname || "127.0.0.1";
    const protocol = window.location.protocol === "https:" ? "https" : "http";
    return `${protocol}://${host}:5000/notifications/transaction-email`;
}

async function sendTransactionEmail(toEmail, transactionData) {
    if (!toEmail) return;

    try {
        const response = await fetch(getEmailApiUrl(), {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                toEmail,
                transactionData
            })
        });

        if (!response.ok) {
            const errorPayload = await response.text();
            console.error("Email sending failed:", response.status, errorPayload);
            return;
        }

        console.log("Transaction email sent to", toEmail);
    } catch (error) {
        console.error("Email service error:", error);
    }
}

window.sendTransactionEmail = sendTransactionEmail;
