// This JavaScript will handle showing/hiding the teacher select dropdown
document.addEventListener("DOMContentLoaded", function() {
    const llmRadio = document.getElementById('llm');
    const teacherRadio = document.getElementById('teacher');
    const teacherSelect = document.getElementById('teacher_select');

    // Initially hide the teacher select dropdown
    teacherSelect.style.display = 'none';

    // Add event listeners for the radio buttons
    llmRadio.addEventListener('change', function() {
        if (llmRadio.checked) {
            teacherSelect.style.display = 'none'; // Hide teacher select when "Ask LLM" is selected
        }
    });

    teacherRadio.addEventListener('change', function() {
        if (teacherRadio.checked) {
            teacherSelect.style.display = 'block'; // Show teacher select when "Ask Teacher" is selected
        }
    });
});
