document.getElementById("uploadForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const pdfFile = document.getElementById("pdfFile").files[0];
    const xlsxFile = document.getElementById("xlsxFile").files[0];
    const status = document.getElementById("status");
    const link = document.getElementById("downloadLink");

    if (!pdfFile || !xlsxFile) {
        alert("Selecione os dois arquivos!");
        return;
    }

    const formData = new FormData();
    formData.append("pdf", pdfFile);
    formData.append("xlsx", xlsxFile);

    status.textContent = "⏳ Convertendo...";
    link.style.display = "none";

    try {
        const response = await fetch("http://127.0.0.1:8000/convert", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) throw new Error("Falha ao converter!");

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        link.href = url;
        link.style.display = "block";
        status.textContent = "✅ Conversão concluída!";
    } catch (err) {
        status.textContent = "❌ Erro: " + err.message;
    }
});
