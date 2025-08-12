const fileInput = document.getElementById('upload');
const preview = document.getElementById('preview');
const result = document.getElementById('result');

// Handling file upload and image preview
fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  result.textContent = "Scanning...";
  result.classList.remove("hidden");

  // Image preview
  if (file) {
    const reader = new FileReader();
    reader.onload = () => {
      preview.src = reader.result;
      preview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  }

  // Pack file into FormData
  const formData = new FormData();
  formData.append('image', file);

  // Send to backend
  const response = await fetch("https://wickly.onrender.com/upload", {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  console.log('data keys:', Object.keys(data));
  console.log('probs raw:', data.probabilities);
  
  if (response.ok) {
    // Make sure it's visible
    result.classList.remove('hidden');
    result.style.display = 'block';
    result.style.whiteSpace = 'pre-wrap';

    // Format probabilities
    const probsPercent = Object.entries(data.probabilities || {})
      .map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`)
      .join('\n');

    // Show prediction in bold, percentages below
    result.innerHTML = `<strong>Prediction:</strong> ${data.prediction}<br><br>${probsPercent}`;
  } else {
    result.classList.remove('hidden');
    result.style.display = 'block';
    result.innerText = data.message || 'Upload failed';
  }
});