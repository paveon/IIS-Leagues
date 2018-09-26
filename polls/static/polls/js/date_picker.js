$(document).ready(function(){
  let date_input=$('.date_picker'); //our date input has the name "date"
  let container="body";
  let options={
    format: 'mm/dd/yyyy',
    icons: {
        date: "fa fa-calendar"
    },
    container: container,
    todayHighlight: true,
    autoclose: true,
  };
  date_input.datepicker(options);
});