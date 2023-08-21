
// Get the slider element
var slider = document.getElementById("slider");

// Get the paragraph element where the slider value will be displayed
var sliderValueElement = document.getElementById("sliderValue");

// Update the paragraph element with the current slider value
sliderValueElement.innerHTML = "Slider Value: " + slider.value;

// Add an event listener to update the value whenever the slider is moved
slider.addEventListener("input", function() {
    sliderValueElement.innerHTML = "Slider Value: " + slider.value;
        });
