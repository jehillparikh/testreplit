document.addEventListener('DOMContentLoaded', function() {
    let currentStep = 1;
    const totalSteps = 5;
    const progressBar = document.getElementById('registrationProgress');
    let userData = {};

    // Update progress bar
    function updateProgress() {
        const progress = ((currentStep - 1) / totalSteps) * 100;
        progressBar.style.width = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
        progressBar.textContent = Math.round(progress) + '%';
    }

    // Show specific step
    function showStep(step) {
        document.querySelectorAll('.registration-step').forEach(el => {
            el.style.display = 'none';
        });
        document.getElementById('step' + step).style.display = 'block';
        currentStep = step;
        updateProgress();
    }

    // Handle next step buttons
    document.querySelectorAll('.next-step').forEach(button => {
        button.addEventListener('click', async function(e) {
            const currentForm = this.closest('form');
            if (!currentForm.checkValidity()) {
                currentForm.reportValidity();
                return;
            }

            if (currentStep === 1) {
                // Basic information validation
                const formData = new FormData(currentForm);
                try {
                    const response = await fetch('/register', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (data.error) {
                        alert(data.error);
                        return;
                    }
                    userData = { ...userData, ...data };
                } catch (error) {
                    alert('Error during registration. Please try again.');
                    return;
                }
            }

            showStep(currentStep + 1);
        });
    });

    // Handle previous step buttons
    document.querySelectorAll('.prev-step').forEach(button => {
        button.addEventListener('click', function() {
            showStep(currentStep - 1);
        });
    });

    // Camera handling for face verification
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const selfiePreview = document.getElementById('selfiePreview');
    let stream = null;

    document.getElementById('startCamera').addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
            video.style.display = 'block';
            document.getElementById('startCamera').style.display = 'none';
            document.getElementById('takePhoto').style.display = 'block';
            video.play();
        } catch (err) {
            alert('Error accessing camera: ' + err.message);
        }
    });

    document.getElementById('takePhoto').addEventListener('click', () => {
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL('image/jpeg');
        selfiePreview.src = imageData;
        selfiePreview.style.display = 'block';
        video.style.display = 'none';
        document.getElementById('takePhoto').style.display = 'none';
        document.getElementById('retakePhoto').style.display = 'block';
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    });

    document.getElementById('retakePhoto').addEventListener('click', () => {
        selfiePreview.style.display = 'none';
        document.getElementById('retakePhoto').style.display = 'none';
        document.getElementById('startCamera').style.display = 'block';
    });

    // Complete registration
    document.getElementById('completeRegistration').addEventListener('click', async function() {
        const bankForm = document.getElementById('bankForm');
        if (!bankForm.checkValidity()) {
            bankForm.reportValidity();
            return;
        }

        try {
            const formData = new FormData(bankForm);
            const response = await fetch('/api/kyc/verify-bank', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }

            // Redirect to dashboard on success
            window.location.href = '/dashboard';
        } catch (error) {
            alert('Error completing registration. Please try again.');
        }
    });

    // Initialize first step
    showStep(1);
});
