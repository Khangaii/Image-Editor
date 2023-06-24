alert("Hello World");

var photos = document.getElementById("photos");

document.getElementById("add_photo").addEventListener("click", add_photo);

// 이해 안 되니까 너 해 봐
function add_photo() {
  let url = "/new_image";
  fetch(url)
  .then(response=>response.text())
  .then(data=> {
    let image_url = "../images/" + data;

    gallery = document.getElementById("gallery");

    image = document.createElement('img');
    image.setAttribute("src", image_url);
    // image.onclick = edit_photo();

    gallery.appendChild(image);
  });
}

// function edit_photo () {
//   // 다시 편집 실행
// }