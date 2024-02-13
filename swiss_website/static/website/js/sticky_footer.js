$(window).bind("load", function() { 
       
       var footerHeight = 0,
           footerTop = 0,
           $footer = $("#footer");
           
       positionFooter();
       
       function positionFooter() {
       
                footerHeight = $footer.height();
                footerTop = ($(window).scrollTop()+$(window).height()-footerHeight)+"px";
		pageHeight = $('.page-content-wrapper').height();
		pageWidth = $('.page-content-wrapper').width();
       
               if ( (pageHeight+footerHeight) < $(window).height()) {
                   $footer.css({
                        position: "absolute",
			width: pageWidth,
                   }).animate({
                        top: footerTop
                   })
               } else {
                   $footer.css({
                        position: "static"
                   })
               }
       }

       $(window)
               .scroll(positionFooter)
               .resize(positionFooter)
});
