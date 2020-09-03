# Javascript

### Dosyaların derlenmesi
Javascript dosyalarını derlemek için öncelikle gereksinimleri yüklememiz gerekiyor. Proje
ana dizinindeyken:

    npm install
    

Bu aşamadan sonra herhangi bir bundler kullanarak dosyaları derleyebilirsiniz.
Bu projede derleme için `parcel`'in ikinci sürümü kullanılıyor. Parcel yüklemek için:

    npm install parcel@2.0.0-beta.1

Eğer bu aşamada Parcel'in daha stabil bir versiyonu bulunuyor ise onu yüklemelisiniz. Derleme
yapmak için `index.js` dosyasının bulunduğu dizinde:

    parcel build index.js --dist-dir dist --no-source-maps
    
Bu aşmadan sonra `dist` dizininde `index.js` adında derlenmiş bir dosya oluşacaktır.