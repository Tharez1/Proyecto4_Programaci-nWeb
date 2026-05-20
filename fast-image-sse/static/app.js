document.addEventListener("DOMContentLoaded", () => {

    const fileInput = document.getElementById("fileInput");

    fileInput.addEventListener("change", async (event) => {

        const file = event.target.files[0];

        if (!file) return;

        // 1. pedir signed POST
        const response = await fetch("/api/presigned-post", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                file_name: file.name,
                file_type: file.type
            })
        });

        const data = await response.json();
        const fileName = data.file_name;
        const presigned = data.presigned;

        console.log(presigned);
        console.log(fileName);

        // 2. construir multipart/form-data
        const formData = new FormData();

        // IMPORTANTISIMO:
        // agregar TODOS los fields primero

        Object.entries(presigned.fields).forEach(([key, value]) => {
            formData.append(key, value);
        });

        // al final el archivo
        formData.append("file", file);

        // 3. subir directo a S3
        const uploadResponse = await fetch(presigned.url, {
            method: "POST",
            body: formData
        });

    if (uploadResponse.ok) {
        console.log("Archivo subido correctamente");

        const source = new EventSource(`/events/${fileName}`);

        source.onmessage = (event) => {
            const data = JSON.parse(event.data);

            console.log("SSE:", data);

            if (data.content === fileName) {
                console.log("Imagen procesada:", data.content);

                document.getElementById("status").textContent =
                    `Imagen procesada: ${data.content}`;

                source.close();
            } else {
                document.getElementById("status").textContent =
                    "Procesando imagen...";
            }
        };

        source.onerror = () => {
            console.error("Error SSE");
            document.getElementById("status").textContent =
                "Esperando respuesta del servidor...";
        };

    } else {
        console.error("Error upload");
    };

   });
});
