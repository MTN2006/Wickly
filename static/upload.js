const fileInput = document.getElementById('upload');
const preview = document.getElementById('preview');
const result = document.getElementById('result');

// Handling file upload and image preview
fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  console.log('Scanning...');
  result.textContent = "Scanning...";
  result.classList.remove("hidden");

  // image preview
  // 1. Grab file input and image elements
  // 2. When the input changes (user picks a file)
  // 3. Get the file
  // 4. Use FileReader to convert it to a Data URL
  // 5. When FileReader is done, show the preview by: setting the image's src and making the image visable
  if (file) {
    const reader = new FileReader();
    reader.onload = () => {
      preview.src = reader.result;
      preview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  }

  // Actually packing the file using FormData
  const formData = new FormData();
  formData.append('image', file);

  // ASYNC/POST sending the file to flask backend
  const response = await fetch("https://wickly.onrender.com/upload", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  console.log('data keys:', Object.keys(data));
  console.log('probs raw:', data.probabilities);
  
  if (response.ok){
    console.log("Good", data.message);
    console.log("Prediction: ", data.prediction);
    console.log("Probabilities: ", data.probabilities);
    const probsPercent = {};
    for (const [label, value] of Object.entries(data.probabilities)) {
        probsPercent[label] = (value * 100).toFixed(1) + "%";
    }

    result.textContent = `Prediction: ${data.prediction} | ${JSON.stringify(probsPercent)}`;



  } else {
    console.log("Bad", data.message);
  }
  result.textContent = data.message;
});


