
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <queue>
#include <iostream>
#include <vector>
#include "CImg.h"


using namespace std;
using namespace cimg_library;

class Punkt
{
public:
  int x;
  int y;
  int z;
  int c;

  Punkt(){}
  Punkt(int X,int Y,int Z,int C) {x=X;y=Y;z=Z;c=C;}
};

struct segment
{
    queue<Punkt> processed;
    queue<Punkt> front;
    queue<Punkt> newFront;
};


#define PROCESSED  2
#define UNPROCESSED 1
#define FRONT 3

int main( int argc, char** argv )
{
    CImg<unsigned char> tchawica;
    CImg<unsigned char> segmentacja;

    segmentacja.load_analyze("DUM1.nii");
    tchawica.load_analyze("DUM2.nii");

    //(tchawica+segmentacja).display();

    int Ni = tchawica.width();
    int Nj = tchawica.height();
    int Nk = tchawica.depth();

    CImg<unsigned char> klastry(Ni,Nj,Nk);
    CImg<unsigned char> processed(Ni,Nj,Nk);
    CImg<unsigned short> distances(Ni,Nj,Nk);

    processed = segmentacja;
    processed += tchawica;

    klastry.fill(0);
    distances.fill(0);

    struct segment segmenty[2000];
    int propagationStep = 1;
    int nlabels = 0;


    CImg<unsigned int> dum(Ni,Nj,Nk);
    queue<Punkt> front;

/************************************************/
/**********   inicjalizacja    ******************/
/************************************************/

    dum.fill(0);
    for (int i=0;i<Ni;i++)
    for (int j=0;j<Nj;j++)
    for (int k=0;k<Nk;k++)
    {
        if (tchawica(i,j,k))
        {
            int flag = 0;
            for(int i1=-1;i1<=1;i1++)
            for(int j1=-1;j1<=1;j1++)
            for(int k1=-1;k1<=1;k1++)
            {
                if (i+i1<0 || i+i1>=Ni || j+j1<0 || j+j1>=Nj || k+k1<0 || k+k1>=Nk)
                    continue;
                if (processed(i+i1,j+j1,k+k1)==UNPROCESSED)
                {
                    flag = 1;
                }
            }
            if (flag==1)
            {
                front.push(Punkt(i,j,k,propagationStep));
                distances(i,j,k) = propagationStep;
                processed(i,j,k) = FRONT;
                dum(i,j,k) = 1;
            }
        }
    }

    while (front.size())
    {
	    Punkt punkt = front.front();
	    front.pop();
	    int I = punkt.x;
	    int J = punkt.y;
	    int K = punkt.z;
        int C = punkt.c;
        if (dum(I,J,K) == 1)
        {
            nlabels++;
            queue<Punkt> klaster;
            klaster.push(punkt);
            dum(I,J,K) = 0;
            klastry(I,J,K) = nlabels;
            while (klaster.size())
            {
	            punkt = klaster.front();
	            klaster.pop();
                segmenty[nlabels-1].front.push(punkt);
	            I = punkt.x;
	            J = punkt.y;
	            K = punkt.z;
                C = punkt.c;
                for(int i1=-1;i1<=1;i1++)
                for(int j1=-1;j1<=1;j1++)
                for(int k1=-1;k1<=1;k1++)
                {
                    if (I+i1<0 || I+i1>=Ni || J+j1<0 || J+j1>=Nj || K+k1<0 || K+k1>=Nk)
                        continue;
                    if (dum(I+i1,J+j1,K+k1)==1)
                    {
                        klaster.push(Punkt(I+i1,J+j1,K+k1,C));
                        dum(I+i1,J+j1,K+k1) = 0;
                        klastry(I+i1,J+j1,K+k1) = nlabels;
                    }
                }
            }
        }
    } 

//    klastry.display("klastry"); 
//    processed.display("processed");

/************************************************/
/*****           główna pętla               *****/
/************************************************/

    while (1)
    {

        propagationStep++;
        printf("propagation step %d %d\n",propagationStep,nlabels);

        int flag = 0;
        for(int nseg=0;nseg<nlabels;nseg++)
        {
            if (segmenty[nseg].front.size())
                flag = 1;
        }
        
        if (flag==0) break;

//        for(int nseg=0;nseg<nlabels;nseg++)
//            printf("%d %d\n",nseg,segmenty[nseg].front.size());

//        if (propagationStep%5==0)
//        {
//            klastry.display("klastry"); 
//            processed.display("processed");
//        }

        int oldNlabels = nlabels;
        dum.fill(0);
        for(int nseg=0;nseg<oldNlabels;nseg++)
        {
	        while (segmenty[nseg].front.size())
	        {
		        Punkt punkt = segmenty[nseg].front.front();
		        segmenty[nseg].front.pop();
		        int I = punkt.x;
		        int J = punkt.y;
		        int K = punkt.z;
                int C = punkt.c;
                segmenty[nseg].processed.push(punkt);

                if (processed(I,J,K) !=FRONT) printf("err\n");
                processed(I,J,K) = PROCESSED;

                for(int i1=-1;i1<=1;i1++)
                for(int j1=-1;j1<=1;j1++)
                for(int k1=-1;k1<=1;k1++)
                {
                    if (I+i1<0 || I+i1>=Ni || J+j1<0 || J+j1>=Nj || K+k1<0 || K+k1>=Nk)
                        continue;
                    if (processed(I+i1,J+j1,K+k1) == UNPROCESSED && dum(I+i1,J+j1,K+k1)==0)
                    {
                        segmenty[nseg].newFront.push(Punkt(I+i1,J+j1,K+k1,propagationStep));
                        klastry(I+i1,J+j1,K+k1) = 1;
                        distances(I+i1,J+j1,K+k1) = propagationStep;
                        dum(I+i1,J+j1,K+k1) = 1;
                        processed(I+i1,J+j1,K+k1) = FRONT;
                    }
                }
            }
        }

        for(int nseg=0;nseg<oldNlabels;nseg++)
        {
            int nl = 0;
            while (segmenty[nseg].newFront.size())
            {
	            Punkt punkt = segmenty[nseg].newFront.front();
	            segmenty[nseg].newFront.pop();
	            int I = punkt.x;
	            int J = punkt.y;
	            int K = punkt.z;
                int C = punkt.c;
                if (dum(I,J,K) == 1)
                {
                    nl++;
                    queue<Punkt> klaster;
                    klaster.push(punkt);
                    dum(I,J,K) = 0;
                    if (nl==1)
                    {
                        klastry(I,J,K) = nseg + 1;
                    }
                    else
                    {
                        nlabels++;
                        klastry(I,J,K) = nlabels;
                    }

                    while (klaster.size())
                    {
	                    punkt = klaster.front();
	                    klaster.pop();
                        if (nl==1)
                            segmenty[nseg].front.push(punkt);
                        else
                            segmenty[nlabels].front.push(punkt);
	                    I = punkt.x;
	                    J = punkt.y;
	                    K = punkt.z;
                        C = punkt.c;
                        for(int i1=-1;i1<=1;i1++)
                        for(int j1=-1;j1<=1;j1++)
                        for(int k1=-1;k1<=1;k1++)
                        {
                            if (I+i1<0 || I+i1>=Ni || J+j1<0 || J+j1>=Nj || K+k1<0 || K+k1>=Nk)
                                continue;
                            if (dum(I+i1,J+j1,K+k1)==1)
                            {
                                klaster.push(Punkt(I+i1,J+j1,K+k1,C));
                                dum(I+i1,J+j1,K+k1) = 0;
                                if (nl==1)
                                    klastry(I+i1,J+j1,K+k1) = nseg + 1;
                                else
                                    klastry(I+i1,J+j1,K+k1) = nlabels;
                            }
                        }
                    }

                    if (nl>1)
                    {
                        int SIZE_TH = 20;
                        if (segmenty[nlabels].front.size()<SIZE_TH)
                        {
                            while (segmenty[nlabels].front.size())
                            {
                                punkt = segmenty[nlabels].front.front();
	                            segmenty[nlabels].front.pop();
                                processed(punkt.x,punkt.y,punkt.z) = PROCESSED;
                                klastry(punkt.x,punkt.y,punkt.z) = 0;
                            }
                            nlabels--;
                        }
                    }
                }
            } 
            
        }

    }

    //klastry.display("klastry"); 
    //processed.display("processed");
    //distances.display("distances");

    klastry.save_raw("CLUSTERS.nii");
    distances.save_raw("DISTANCES.nii");


    return 0;
}

